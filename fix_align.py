import os
import glob
import sys

# old_path = 'preprocessed_data/infore/TextGrid/infore1'
# new_path = 'preprocessed_data/infore/TextGrid/infore/'

data_path = sys.argv[1]

# def fix_grid(in_file, out_file):
#     if os.path.exists(in_file):
#         with open(in_file, 'r', encoding='utf-8') as fin:
#             with open(out_file, 'w', encoding='utf-8') as fout:
#                 is_start = False
#                 for line in fin:
#                     if is_start:
#                         if 'text = ""' in line:
#                             fout.write(line.replace('text = ""', 'text = "sp"').rstrip() + '\n')
#                         else:
#                             fout.write(line.rstrip() + '\n')
#                     else:
#                         if 'name = "phones"' in line:
#                             is_start = True
#                         fout.write(line.rstrip() + '\n')
#                 print(' - Fixed: ', os.path.basename(in_file))

def fix_grid(in_file, out_file):
    result = False
    if os.path.exists(in_file):
        got_spn = False
        is_start = False
        lines = []
        count_accept = 0
        with open(in_file, 'r', encoding='utf-8') as fin:
            for line in fin:
                if is_start:
                    if 'text = "spn"' in line:
                        got_spn = True
                        break
                    elif 'text = ""' in line:
                        lines.append(line.replace('text = ""', 'text = "sp"').rstrip() + '\n')
                        result = True
                    else:
                        lines.append(line.rstrip() + '\n')
                        if 'text = "' in line:
                            count_accept += 1
                else:
                    if 'name = "phones"' in line:
                        is_start = True
                    lines.append(line.rstrip() + '\n')
        if not got_spn and count_accept>5:
            with open(out_file, 'w', encoding='utf-8') as fout:
                fout.writelines(lines)
                    #print(' - Fixed: ', os.path.basename(in_file)) 
        else:
                result = False

    return result 

grids = glob.glob(data_path+'/*.TextGrid')

count = 0;
totalCount = 0;

for fin in grids:
    if os.path.isfile(fin):
        totalCount += 1
        if fix_grid(fin, fin):
            count += 1

print('Done! Total: ', count, '/', totalCount)