@echo off
conda create -n nat2
conda activate nat2
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
REM conda install pytorch torchvision torchaudio pytorch-cuda=12.4 -c pytorch -c nvidia
pip install -r requirements.txt