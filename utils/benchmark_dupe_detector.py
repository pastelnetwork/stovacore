import os
import pickle
import sys
import hashlib

import pandas as pd
from PastelCommon.dupe_detection import DupeDetector
from core_modules.blackbox_modules.dupe_detection_utils import measure_similarity, assemble_fingerprints_for_pandas

# PATH HACK
from core_modules.settings import NetWorkSettings

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")


def get_sha256_hash_of_input_data_func(input_data_or_string):
    if isinstance(input_data_or_string, str):
        input_data_or_string = input_data_or_string.encode('utf-8')
    sha256_hash_of_input_data = hashlib.sha3_256(input_data_or_string).hexdigest()
    return sha256_hash_of_input_data


def list_files(basedir):
    files = []
    for i in sorted(os.listdir(basedir)):
        if i.split(".")[-1] in ["jpg", "jpeg", "bmp", "gif", "png"]:
            files.append(os.path.join(basedir, i))
    return files


def get_fingerprint_for_file(current_image_file_path):
    # read the actual image file
    data = open(current_image_file_path, 'rb').read()

    # compute hash
    imghash = get_sha256_hash_of_input_data_func(data)

    fingerprints = DupeDetector(NetWorkSettings.DUPE_DETECTION_MODELS, NetWorkSettings.DUPE_DETECTION_TARGET_SIZE).compute_deep_learning_features(data)
    return imghash, fingerprints


def populate_fingerprint_db(basedir):
    files = list_files(basedir)
    db = {}
    counter = 0
    for current_image_file_path in files:
        print('Now adding image file %s to image fingerprint database: %s/%s' % (current_image_file_path,
                                                                                 counter, len(files)))

        imghash, fingerprints = get_fingerprint_for_file(current_image_file_path)

        # add to the database
        db[imghash] = (current_image_file_path, fingerprints)
        counter += 1
    return db


def compute_fingerprint_for_single_image(filepath):
    imagehash, fingerprints = get_fingerprint_for_file(filepath)

    A = pd.DataFrame([imagehash, filepath]).T
    B = pd.DataFrame(fingerprints)
    combined_image_fingerprint_df_row = pd.concat([A, B], axis=1, join_axes=[A.index])
    fingerprint = combined_image_fingerprint_df_row.iloc[:,2:].T.values.flatten().tolist()
    return fingerprint


def test_files_for_duplicates(dupe_images, pandas_table):
    filelist = list_files(dupe_images)

    dupes = []
    for filename in filelist:
        print('Testing file: ' + filename)

        # compute fingerprint
        _, fingerprints = get_fingerprint_for_file(filename)
        is_likely_dupe, params_df = measure_similarity(fingerprints, pandas_table)

        if is_likely_dupe:
            print("Art file (%s) appears to be a DUPLICATE!" % filename)
            dupes.append(filename)
        else:
            print("Art file (%s) appears to be an ORIGINAL!" % filename)

        print('Parameters for current image:')
        print(params_df)

    dupe_percentage = len(dupes) / len(filelist)
    return dupe_percentage


if __name__ == "__main__":
    # parse parameters
    image_root = sys.argv[1]
    database_filename = sys.argv[2]
    regenerate = False
    if len(sys.argv) > 3 and sys.argv[3] == "regenerate":
        regenerate = True

    # folder structure
    all_works = os.path.join(image_root, 'all_works')
    dupe_images = os.path.join(image_root, 'dupes')
    nondupe_images = os.path.join(image_root, 'nondupes')

    # do we need to regenerate the DB?
    if regenerate:
        print("Regenerate is True, generating fingerprint database")
        key = input("Would you like to overwrite %s (y/n): " % database_filename)
        if key == "y":
            with open(database_filename, "wb") as f:
                fingerprint_db = populate_fingerprint_db(all_works)
                f.write(pickle.dumps(fingerprint_db))
        print("Done")
        exit()
    else:
        print("Regenerate is False, loading from disk: %s" % database_filename)
        fingerprint_db = pickle.load(open(database_filename, "rb"))
        print("Loaded %s fingerprints" % len(fingerprint_db))

    # assemble fingerprints
    pandas_table = assemble_fingerprints_for_pandas([(k, v) for k, v in fingerprint_db.items()])

    # tests
    print('Now testing duplicate-detection scheme on known near-duplicate images')
    dupe_percentage = test_files_for_duplicates(dupe_images, pandas_table)
    print('\nAccuracy Percentage in Detecting Duplicate Images: %.2f%%' % (dupe_percentage*100))

    print('Now testing duplicate-detection scheme on known non-duplicate images')
    dupe_percentage = test_files_for_duplicates(nondupe_images, pandas_table)
    print('\nAccuracy Percentage in Detecting Non-Duplicate Images: %.2f%%' % ((1-dupe_percentage)*100))
