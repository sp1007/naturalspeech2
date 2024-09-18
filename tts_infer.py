import json
import re
import argparse
from string import punctuation
from vocos import Vocos

import torch
import torchaudio
import torchaudio.transforms as T
import yaml
import numpy as np
import os
from torch.utils.data import DataLoader
from g2p_en import G2p
from model import NaturalSpeech2
from pypinyin import pinyin, Style

from ema_pytorch import EMA
from text import text_to_sequence


def read_lexicon(lex_path):
    lexicon = {}
    with open(lex_path) as f:
        for line in f:
            temp = re.split(r"\s+", line.strip("\n"))
            word = temp[0]
            phones = temp[1:]
            if word.lower() not in lexicon:
                lexicon[word.lower()] = phones
    return lexicon


def preprocess_english(text, preprocess_config):
    text = text.rstrip(punctuation)
    lexicon = read_lexicon('./lexicons/librispeech-lexicon.txt')

    g2p = G2p()
    phones = []
    words = re.split(r"([,;.\-\?\!\s+])", text)
    for w in words:
        if w.lower() in lexicon:
            phones += lexicon[w.lower()]
        else:
            phones += list(filter(lambda p: p != " ", g2p(w)))
    phones = "{" + "}{".join(phones) + "}"
    phones = re.sub(r"\{[^\w\s]?\}", "{sp}", phones)
    phones = phones.replace("}{", " ")

    print("Raw Text Sequence: {}".format(text))
    print("Phoneme Sequence: {}".format(phones))
    cleaners = ["english_cleaners"]
    sequence = np.array(
        text_to_sequence(
            phones, cleaners
        )
    )

    return np.array(sequence)


def preprocess_mandarin(text, preprocess_config):
    lexicon = read_lexicon('./mandarin_mfa_tools/simple.txt')

    phones = []
    pinyins = [
        p[0]
        for p in pinyin(
            text, style=Style.TONE3, strict=False, neutral_tone_with_five=True
        )
    ]
    for p in pinyins:
        if p in lexicon:
            phones += lexicon[p]
        else:
            phones.append("sp")

    phones = "{" + " ".join(phones) + "}"
    print("Raw Text Sequence: {}".format(text))
    print("Phoneme Sequence: {}".format(phones))
    cleaners = []
    sequence = np.array(
        text_to_sequence(
            phones, cleaners
        )
    )

    return np.array(sequence)


def synthesize(model, cfg, vocos, batchs, control_values, device):
    pitch_control, energy_control, duration_control = control_values

    for batch in batchs:
        phoneme, refer_path, phoneme_length = batch 
        phoneme = torch.LongTensor(phoneme).to(device)
        phoneme_length = torch.LongTensor(phoneme_length).to(device)
        refer_audio,sr = torchaudio.load(refer_path)
        refer_audio24k = T.Resample(sr, 24000)(refer_audio)
        spec_process = torchaudio.transforms.MelSpectrogram(
            sample_rate=24000,
            n_fft=1024,
            hop_length=256,
            n_mels=100,
            center=True,
            power=1,
        )
        spec = spec_process(refer_audio24k).to(device)# 1 100 T
        spec = torch.log(torch.clip(spec, min=1e-7))
        refer = spec
        refer_length = torch.tensor([refer.size(1)]).to(device)
        # print(refer.shape)
        with torch.no_grad():
            samples,mel = model.sample(phoneme, refer, phoneme_length, refer_length, vocos)
            samples = samples.detach().cpu()
    return samples
def load_model(model_path, device, cfg):
    data = torch.load(model_path, map_location=device)
    model = NaturalSpeech2(cfg=cfg)
    model.load_state_dict(data['model'])

    model.to(device)
    return model.eval()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--text",
        type=str,
        default="你好再见",
        help="raw text to synthesize, for single-sentence mode only",
    )
    parser.add_argument(
        "--lang",
        type=str,
        choices=["en", "zh"],
        default="zh",
        help="language of the input text",
    )
    parser.add_argument(
        "--refer",
        type=str,
        default="test1.wav",
        help="reference audio path for single-sentence mode only",
    )
    parser.add_argument(
        # "-c", "--config_path", type=str, default="config.json", help="path to config.json"
        "-c", "--config_path", type=str, default="config.json", help="path to config.json"
    )
    parser.add_argument(
        # "-m", "--model_path", type=str, default="logs/tts/model-1000.pt", help="path to model.pt"
        "-m", "--model_path", type=str, default="logs/tts/2023-08-29-10-58-23/model-18.pt", help="path to model.pt"
    )
    parser.add_argument(
        "--pitch_control",
        type=float,
        default=1.0,
        help="control the pitch of the whole utterance, larger value for higher pitch",
    )
    parser.add_argument(
        "--energy_control",
        type=float,
        default=1.0,
        help="control the energy of the whole utterance, larger value for larger volume",
    )
    parser.add_argument(
        "--duration_control",
        type=float,
        default=1.0,
        help="control the speed of the whole utterance, larger value for slower speaking rate",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda:0",
        help="specify the device, cpu or cuda",
    )
    args = parser.parse_args()

    device = args.device
    # Check source texts
    assert args.text is not None

    # Read Config

    cfg = json.load(open(args.config_path))

    # Get model
    model = load_model(args.model_path, device, cfg)

    # Load vocoder
    vocos = Vocos.from_pretrained("charactr/vocos-mel-24khz")

    ids = raw_texts = [args.text[:100]]
    if args.lang == "en":
        texts = np.array([preprocess_english(args.text, cfg)])
    elif args.lang == "zh":
        texts = np.array([preprocess_mandarin(args.text, cfg)])
    text_lens = np.array([len(texts[0])])
    raw_path = 'raw'
    refer_name = args.refer
    refer_path = f"{raw_path}/{refer_name}"
    batchs = [( texts,refer_path,text_lens)]

    control_values = args.pitch_control, args.energy_control, args.duration_control

    audios = synthesize(model, cfg, vocos, batchs, control_values, device)

    results_folder = "output"
    result_path = f'./{results_folder}/tts_{refer_name}.wav'
    if not os.path.exists(results_folder):
        os.makedirs(results_folder)
    torchaudio.save(result_path, audios, 24000)
