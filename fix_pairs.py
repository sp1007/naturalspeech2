import os
import glob
import sys

data_path = sys.argv[1]

def remove_empty(src_filename, ext='wav'):
    if os.path.exists(src_filename):
        dest_filename = os.path.splitext(src_filename)[0] + '.' + ext
        if not os.path.exists(dest_filename):
            os.remove(src_filename)
            return True
    return False

def check_files(src_ext = 'lab', dest_ext = 'wav'):
    print("Start checking file {} vs {} in {} ...".format(src_ext, dest_ext, data_path))
    files = glob.glob(data_path + '/*.' + src_ext)
    count = 0
    for fin in files:
        if os.path.isfile(fin):
            if remove_empty(fin, dest_ext):
                count += 1
    print("Done!")
    
check_files()
check_files(src_ext='wav', dest_ext='lab')