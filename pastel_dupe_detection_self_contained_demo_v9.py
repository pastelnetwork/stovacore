import hashlib, sqlite3, imghdr, glob, os, io, time, random, base64, functools, psutil, warnings #Python stdlib
import scipy
import minepy
import numpy as np
import pandas as pd
from scipy import stats
import zstandard as zstd
from scipy.stats import rankdata
import sklearn.metrics
from os import devnull
import tensorflow as tf
import matplotlib.pyplot as plt
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.imagenet_utils import preprocess_input
from tensorflow.keras import applications
from multiprocessing import cpu_count, freeze_support
from functools import reduce
from sklearn.manifold import TSNE
from pathos.pools import ProcessPool
from contextlib import contextmanager,redirect_stderr,redirect_stdout

# Notes:
# If you have Anaconda installed, you probably already have these:
# conda install -c anaconda scipy
# conda install -c anaconda pandas
# conda install -c anaconda numpy
# But you might need to install these:
# conda install -c conda-forge tensorflow
# conda install -c conda-forge pathos
# conda install -c bioconda minepy
# To run the code, you need to first download the test files here as zip files and extract them to the folders shown below:
# Registered images to populate the image fingerprint database: 
# https://www.dropbox.com/s/6ohzgvz418rhl4l/Animecoin_All_Finished_Works.zip?dl=0
# Near-Duplicate images for testing: 
# https://www.dropbox.com/s/4uajzyh09bc0rp3/dupe_detector_test_images.zip?dl=0
# Non-Duplicate images to check for false positives: 
# https://www.dropbox.com/s/yjqsxsz97msai4e/non_duplicate_test_images.zip?dl=0
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
pd.options.mode.chained_assignment = None  # default='warn'
warnings.simplefilter(action='ignore', category=FutureWarning)
np_settings = np.seterr(divide='ignore', invalid='ignore')
np.random.seed(42)
random.seed(12345)
tf.compat.v1.set_random_seed(1234)
parent = psutil.Process()
parent.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)

use_demonstrate_duplicate_detection = 1

if __name__ == '__main__':
    root_pastel_folder_path = '/Users/jeffr/pastel/'
    misc_masternode_files_folder_path = os.path.join(root_pastel_folder_path, 'misc_masternode_files' + os.sep) #Where we store some of the SQlite databases
    dupe_detection_image_fingerprint_database_file_path = os.path.join(root_pastel_folder_path, 'dupe_detection_image_fingerprint_database.sqlite')
    path_to_all_registered_works_for_dupe_detection =  os.path.join(root_pastel_folder_path, 'Animecoin_All_Finished_Works'+ os.sep)
    dupe_detection_test_images_base_folder_path =  os.path.join(root_pastel_folder_path, 'dupe_detector_test_images'+ os.sep) #Stress testing with sophisticated "modified" duplicates
    non_dupe_test_images_base_folder_path =  os.path.join(root_pastel_folder_path, 'non_duplicate_test_images'+ os.sep) #These are non-dupes, used to check for false positives.
    try:
        os.mkdir(misc_masternode_files_folder_path)
    except:
        pass

def convert_numpy_array_to_sqlite_func(input_numpy_array):
    """ Store Numpy array natively in SQlite (see: http://stackoverflow.com/a/31312102/190597"""
    output_data = io.BytesIO()
    np.save(output_data, input_numpy_array)
    output_data.seek(0)
    return sqlite3.Binary(output_data.read())

def convert_sqlite_data_to_numpy_array_func(sqlite_data_in_text_format):
    output_data = io.BytesIO(sqlite_data_in_text_format)
    output_data.seek(0)
    return np.load(output_data)

sqlite3.register_adapter(np.ndarray, convert_numpy_array_to_sqlite_func) # Converts np.array to TEXT when inserting
sqlite3.register_converter('array', convert_sqlite_data_to_numpy_array_func) # Converts TEXT to np.array when selecting

class MyTimer():
    def __init__(self):
        self.start = time.time()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.time()
        runtime = end - self.start
        msg = '({time} seconds to complete)'
        print(msg.format(time=round(runtime,2)))

@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)
            
def get_indices_of_k_smallest_func(arr, k):
    idx = np.argpartition(arr.ravel(), k)
    return np.array(np.unravel_index(idx, arr.shape))[:, range(k)].transpose().tolist()

def most_frequently_occurring_element_in_list_func(input_list): 
    return max(set(input_list), key = input_list.count) 

def most_frequently_occuring_list_in_list_of_lists_func(input_list_of_lists):
    simple_list = [element for sublist in input_list_of_lists for element in sublist]
    most_commonly_occurring_list = max(simple_list, key= simple_list.count)
    return most_commonly_occurring_list

def compress_data_with_zstd_func(input_data):
    zstd_compression_level = 22 #Highest (best) compression level is 22
    zstandard_compressor = zstd.ZstdCompressor(level=zstd_compression_level, write_content_size=True)
    zstd_compressed_data = zstandard_compressor.compress(input_data)
    return zstd_compressed_data

def decompress_data_with_zstd_func(zstd_compressed_data):
    zstandard_decompressor = zstd.ZstdDecompressor()
    uncompressed_data = zstandard_decompressor.decompress(zstd_compressed_data)
    return uncompressed_data

def compress_file_with_zstd_func(input_file_path):
    if os.path.exists(input_file_path):
        with open(input_file_path,'rb') as f:
            input_data = f.read()
        filename = os.path.split(input_file_path)[-1]
        zstd_compressed_data = compress_data_with_zstd_func(input_data)
    compressed_output_filename = os.path.split(input_file_path)[0] + filename +'.zstd'
    with open(compressed_output_filename,'wb') as f:
        f.write(zstd_compressed_data)
    return compressed_output_filename

def decompress_file_with_zstd_func(input_file_path):
    if os.path.exists(input_file_path):
        with open(input_file_path,'rb') as f:
            input_data = f.read()
        filename = os.path.split(input_file_path)[-1]
        uncompressed_data = decompress_data_with_zstd_func(input_data)
    output_filename = os.path.split(input_file_path)[0] + filename.replace('.zstd','')
    with open(output_filename,'wb') as f:
        f.write(uncompressed_data)
    return output_filename

def get_sha256_hash_of_input_data_func(input_data_or_string):
    if isinstance(input_data_or_string, str):
        input_data_or_string = input_data_or_string.encode('utf-8')
    sha256_hash_of_input_data = hashlib.sha3_256(input_data_or_string).hexdigest()
    return sha256_hash_of_input_data

def get_image_hash_from_image_file_path_func(path_to_art_image_file):
    try:
        with open(path_to_art_image_file,'rb') as f:
            art_image_file_binary_data = f.read()
        sha256_hash_of_art_image_file = get_sha256_hash_of_input_data_func(art_image_file_binary_data)
        return sha256_hash_of_art_image_file
    except Exception as e:
        print('Error: '+ str(e))

def check_if_file_path_is_a_valid_image_func(path_to_file):
    is_image = 0
    if (imghdr.what(path_to_file) == 'gif') or (imghdr.what(path_to_file) == 'jpeg') or (imghdr.what(path_to_file) == 'png') or (imghdr.what(path_to_file) == 'bmp'):
        is_image = 1
        return is_image

def get_all_valid_image_file_paths_in_folder_func(path_to_art_folder):
    valid_image_file_paths = []
    try:
        art_input_file_paths =  glob.glob(path_to_art_folder + os.sep + '*.jpg') + glob.glob(path_to_art_folder + os.sep + '*.jpeg') + glob.glob(path_to_art_folder + os.sep + '*.png') + glob.glob(path_to_art_folder + os.sep + '*.bmp') + glob.glob(path_to_art_folder + os.sep + '*.gif')
        for current_art_file_path in art_input_file_paths:
            if check_if_file_path_is_a_valid_image_func(current_art_file_path):
                valid_image_file_paths.append(current_art_file_path)
        return valid_image_file_paths
    except Exception as e:
        print('Error: '+ str(e))

def regenerate_empty_dupe_detection_image_fingerprint_database_func():
    global dupe_detection_image_fingerprint_database_file_path
    conn = sqlite3.connect(dupe_detection_image_fingerprint_database_file_path, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    dupe_detection_image_fingerprint_database_creation_string= """CREATE TABLE image_hash_to_image_fingerprint_table (sha256_hash_of_art_image_file text, path_to_art_image_file, model_1_image_fingerprint_vector array, model_2_image_fingerprint_vector array, model_3_image_fingerprint_vector array, model_4_image_fingerprint_vector array, model_5_image_fingerprint_vector array, model_6_image_fingerprint_vector array, model_7_image_fingerprint_vector array, datetime_fingerprint_added_to_database TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (sha256_hash_of_art_image_file));"""
    c.execute(dupe_detection_image_fingerprint_database_creation_string)
    conn.commit()
    conn.close()
    
def get_image_file_path_from_image_hash_func(sha256_hash_of_art_image_file):
    try:
        conn = sqlite3.connect(dupe_detection_image_fingerprint_database_file_path, detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        query_results = c.execute("""SELECT path_to_art_image_file FROM image_hash_to_image_fingerprint_table where sha256_hash_of_art_image_file = ? ORDER BY datetime_fingerprint_added_to_database DESC""",[sha256_hash_of_art_image_file,]).fetchall()
        conn.close()
    except Exception as e:
        print('Error: '+ str(e))  
    path_to_art_image_file = query_results[0][0]
    return path_to_art_image_file
    
def get_list_of_all_registered_image_file_hashes_func():
    try:
        conn = sqlite3.connect(dupe_detection_image_fingerprint_database_file_path,detect_types=sqlite3.PARSE_DECLTYPES)
        c = conn.cursor()
        query_results = c.execute("""SELECT sha256_hash_of_art_image_file FROM image_hash_to_image_fingerprint_table ORDER BY datetime_fingerprint_added_to_database DESC""").fetchall()
        conn.close()
    except Exception as e:
        print('Error: '+ str(e))
    list_of_registered_image_file_hashes = [x[0] for x in query_results]
    return list_of_registered_image_file_hashes

def get_named_model_func(model_name):
    if model_name == 'EfficientNetB7':
        return applications.EfficientNetB7(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'NASNetLarge':
        return applications.NASNetLarge(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'ResNet152V2':
        return applications.ResNet152V2(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'InceptionV3':
        return applications.inception_v3.InceptionV3(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'InceptionResNetV2':
        return applications.inception_resnet_v2.InceptionResNetV2(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'EfficientNetB6':
        return applications.EfficientNetB6(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'ResNet50':
        return applications.resnet50.ResNet50(weights='imagenet', include_top=False, pooling='avg')
    if model_name == 'DenseNet201':
        return applications.DenseNet201(weights='imagenet', include_top=False, pooling='avg')   
    raise ValueError('Unknown model')

def prepare_image_fingerprint_data_for_export_func(image_feature_data):
    image_feature_data_arr = np.char.mod('%f', image_feature_data) # convert from Numpy to a list of values
    x_data = np.asarray(image_feature_data_arr).astype('float64') # convert image data to float64 matrix. float64 is need for bh_sne
    image_fingerprint_vector = x_data.reshape((x_data.shape[0], -1))
    return image_fingerprint_vector

def compute_image_deep_learning_features_func(path_to_art_image_file):
    dupe_detection_model_1_name = 'EfficientNetB7'
    dupe_detection_model_2_name = 'EfficientNetB6'
    dupe_detection_model_3_name = 'InceptionResNetV2'
    dupe_detection_model_4_name = 'DenseNet201'
    dupe_detection_model_5_name = 'InceptionV3'
    dupe_detection_model_6_name = 'NASNetLarge'
    dupe_detection_model_7_name = 'ResNet152V2'
    global dupe_detection_model_1
    global dupe_detection_model_2
    global dupe_detection_model_3
    global dupe_detection_model_4
    global dupe_detection_model_5
    global dupe_detection_model_6
    global dupe_detection_model_7

    if not os.path.isfile(path_to_art_image_file):
        return
    else:
        with open(path_to_art_image_file,'rb') as f:
            image_file_binary_data = f.read()
            sha256_hash_of_art_image_file = get_sha256_hash_of_input_data_func(image_file_binary_data)
        img = image.load_img(path_to_art_image_file, target_size=(224, 224)) # load image setting the image size to 224 x 224
        
        x = image.img_to_array(img) # convert image to numpy array
        x = np.expand_dims(x, axis=0) # the image is now in an array of shape (3, 224, 224) but we need to expand it to (1, 2, 224, 224) as Keras is expecting a list of images
        x = preprocess_input(x)
        x = tf.convert_to_tensor(x, dtype=tf.float32)
        dupe_detection_model_1_loaded_already = 'dupe_detection_model_1' in globals()
        if not dupe_detection_model_1_loaded_already:
            print('Loading deep learning model 1 ('+dupe_detection_model_1_name+')...')
            dupe_detection_model_1 = get_named_model_func(dupe_detection_model_1_name)
        
        dupe_detection_model_2_loaded_already = 'dupe_detection_model_2' in globals()
        if not dupe_detection_model_2_loaded_already:
            print('Loading deep learning model 2 ('+dupe_detection_model_2_name+')...')
            dupe_detection_model_2 = get_named_model_func(dupe_detection_model_2_name)
        
        dupe_detection_model_3_loaded_already = 'dupe_detection_model_3' in globals()
        if not dupe_detection_model_3_loaded_already:
            print('Loading deep learning model 3 ('+dupe_detection_model_3_name+')...')
            dupe_detection_model_3 = get_named_model_func(dupe_detection_model_3_name)            
        
        dupe_detection_model_4_loaded_already = 'dupe_detection_model_4' in globals()
        if not dupe_detection_model_4_loaded_already:
            print('Loading deep learning model 4 ('+dupe_detection_model_4_name+')...')
            dupe_detection_model_4 = get_named_model_func(dupe_detection_model_4_name)
        
        dupe_detection_model_5_loaded_already = 'dupe_detection_model_5' in globals()
        if not dupe_detection_model_5_loaded_already:
            print('Loading deep learning model 5 ('+dupe_detection_model_5_name+')...')
            dupe_detection_model_5 = get_named_model_func(dupe_detection_model_5_name)
            
        dupe_detection_model_6_loaded_already = 'dupe_detection_model_6' in globals()
        if not dupe_detection_model_6_loaded_already:
            print('Loading deep learning model 6 ('+dupe_detection_model_6_name+')...')
            dupe_detection_model_6 = get_named_model_func(dupe_detection_model_6_name)            
            
        dupe_detection_model_7_loaded_already = 'dupe_detection_model_7' in globals()
        if not dupe_detection_model_7_loaded_already:
            print('Loading deep learning model 7 ('+dupe_detection_model_7_name+')...')
            dupe_detection_model_7 = get_named_model_func(dupe_detection_model_7_name)            
        
        model_1_features = dupe_detection_model_1.predict(x)[0] # extract the features
        model_2_features = dupe_detection_model_2.predict(x)[0]
        model_3_features = dupe_detection_model_3.predict(x)[0]
        model_4_features = dupe_detection_model_4.predict(x)[0]
        model_5_features = dupe_detection_model_5.predict(x)[0]
        model_6_features = dupe_detection_model_6.predict(x)[0]
        model_7_features = dupe_detection_model_7.predict(x)[0]

        model_1_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_1_features)
        model_2_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_2_features)
        model_3_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_3_features)
        model_4_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_4_features)
        model_5_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_5_features)
        model_6_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_6_features)
        model_7_image_fingerprint_vector = prepare_image_fingerprint_data_for_export_func(model_7_features)
        return model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector, sha256_hash_of_art_image_file, dupe_detection_model_1, dupe_detection_model_2, dupe_detection_model_3, dupe_detection_model_4, dupe_detection_model_5, dupe_detection_model_6, dupe_detection_model_7

def get_image_deep_learning_features_combined_vector_for_single_image_func(path_to_art_image_file):
    model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector, sha256_hash_of_art_image_file, dupe_detection_model_1, dupe_detection_model_2, dupe_detection_model_3, dupe_detection_model_4, dupe_detection_model_5, dupe_detection_model_6, dupe_detection_model_7 = compute_image_deep_learning_features_func(path_to_art_image_file)
    model_1_image_fingerprint_vector_clean = [x[0] for x in model_1_image_fingerprint_vector]
    model_2_image_fingerprint_vector_clean = [x[0] for x in model_2_image_fingerprint_vector]
    model_3_image_fingerprint_vector_clean = [x[0] for x in model_3_image_fingerprint_vector]
    model_4_image_fingerprint_vector_clean = [x[0] for x in model_4_image_fingerprint_vector]
    model_5_image_fingerprint_vector_clean = [x[0] for x in model_5_image_fingerprint_vector]
    model_6_image_fingerprint_vector_clean = [x[0] for x in model_6_image_fingerprint_vector]
    model_7_image_fingerprint_vector_clean = [x[0] for x in model_7_image_fingerprint_vector]
    combined_image_fingerprint_vector = model_1_image_fingerprint_vector_clean + model_2_image_fingerprint_vector_clean + model_3_image_fingerprint_vector_clean + model_4_image_fingerprint_vector_clean + model_5_image_fingerprint_vector_clean + model_6_image_fingerprint_vector_clean + model_7_image_fingerprint_vector_clean
    A = pd.DataFrame([sha256_hash_of_art_image_file, path_to_art_image_file]).T
    B = pd.DataFrame(combined_image_fingerprint_vector).T
    combined_image_fingerprint_df_row = pd.concat([A, B], axis=1)
    combined_image_fingerprint_df_row = combined_image_fingerprint_df_row.reindex(A.index)
    #combined_image_fingerprint_df_row = combined_image_fingerprint_df_row.reset_index()
    return combined_image_fingerprint_df_row


def compress_image_combined_fingerprint_vector_func(candidate_image_fingerprint):
    candidate_image_fingerprint = candidate_image_fingerprint.reset_index()
    candidate_image_fingerprint_json = candidate_image_fingerprint.to_json(orient='values')
    candidate_image_fingerprint_json_compressed_zstd =  compress_data_with_zstd_func(candidate_image_fingerprint_json.encode('utf-8'))
    candidate_image_fingerprint_json_compressed_zstd_base64_encoded = base64.b64encode(candidate_image_fingerprint_json_compressed_zstd)
    return candidate_image_fingerprint_json_compressed_zstd_base64_encoded

def decompress_image_combined_fingerprint_vector_func(candidate_image_fingerprint_json_compressed_zstd_base64_encoded):
    candidate_image_fingerprint_json_compressed_zstd_= base64.b64decode(candidate_image_fingerprint_json_compressed_zstd_base64_encoded)
    candidate_image_fingerprint_json =  decompress_data_with_zstd_func(candidate_image_fingerprint_json_compressed_zstd_).decode('utf-8')
    return candidate_image_fingerprint_json

def add_image_fingerprints_to_dupe_detection_database_func(path_to_art_image_file):
    global dupe_detection_image_fingerprint_database_file_path
    model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector,  sha256_hash_of_art_image_file, dupe_detection_model_1, dupe_detection_model_2, dupe_detection_model_3, dupe_detection_model_4, dupe_detection_model_5, dupe_detection_model_6, dupe_detection_model_7 = compute_image_deep_learning_features_func(path_to_art_image_file)
    conn = sqlite3.connect(dupe_detection_image_fingerprint_database_file_path)
    c = conn.cursor()
    data_insertion_query_string = """INSERT OR REPLACE INTO image_hash_to_image_fingerprint_table (sha256_hash_of_art_image_file, path_to_art_image_file, model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"""
    c.execute(data_insertion_query_string, [sha256_hash_of_art_image_file, path_to_art_image_file, model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector])
    conn.commit()
    conn.close()
    return  model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector

def add_all_images_in_folder_to_image_fingerprint_database_func(path_to_art_folder):
    valid_image_file_paths = get_all_valid_image_file_paths_in_folder_func(path_to_art_folder)
    for current_image_file_path in valid_image_file_paths:
        print('\nNow adding image file '+ current_image_file_path + ' to image fingerprint database.')
        add_image_fingerprints_to_dupe_detection_database_func(current_image_file_path)

def get_all_image_fingerprints_from_dupe_detection_database_as_dataframe_func():
    global dupe_detection_image_fingerprint_database_file_path
    list_of_registered_image_file_hashes = get_list_of_all_registered_image_file_hashes_func()
    conn = sqlite3.connect(dupe_detection_image_fingerprint_database_file_path,detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()
    combined_image_fingerprint_df = pd.DataFrame()
    list_of_combined_image_fingerprint_rows = list()
    for current_image_file_hash in list_of_registered_image_file_hashes:
        # current_image_file_hash = list_of_registered_image_file_hashes[0]
        dupe_detection_fingerprint_query_results = c.execute("""SELECT model_1_image_fingerprint_vector, model_2_image_fingerprint_vector, model_3_image_fingerprint_vector, model_4_image_fingerprint_vector, model_5_image_fingerprint_vector, model_6_image_fingerprint_vector, model_7_image_fingerprint_vector FROM image_hash_to_image_fingerprint_table where sha256_hash_of_art_image_file = ? ORDER BY datetime_fingerprint_added_to_database DESC""",[current_image_file_hash,]).fetchall()
        if len(dupe_detection_fingerprint_query_results) == 0:
            print('Fingerprints for this image could not be found, try adding it to the system!')
        model_1_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][0]
        model_2_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][1]
        model_3_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][2]
        model_4_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][3]
        model_5_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][4]
        model_6_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][5]
        model_7_image_fingerprint_results = dupe_detection_fingerprint_query_results[0][6]

        model_1_image_fingerprint_vector = [x[0] for x in model_1_image_fingerprint_results]
        model_2_image_fingerprint_vector = [x[0] for x in model_2_image_fingerprint_results]
        model_3_image_fingerprint_vector = [x[0] for x in model_3_image_fingerprint_results]
        model_4_image_fingerprint_vector = [x[0] for x in model_4_image_fingerprint_results]
        model_5_image_fingerprint_vector = [x[0] for x in model_5_image_fingerprint_results]
        model_6_image_fingerprint_vector = [x[0] for x in model_6_image_fingerprint_results]
        model_7_image_fingerprint_vector = [x[0] for x in model_7_image_fingerprint_results]

        combined_image_fingerprint_vector = model_1_image_fingerprint_vector + model_2_image_fingerprint_vector + model_3_image_fingerprint_vector + model_4_image_fingerprint_vector + model_5_image_fingerprint_vector + model_6_image_fingerprint_vector + model_7_image_fingerprint_vector
        list_of_combined_image_fingerprint_rows.append(combined_image_fingerprint_vector)
        current_image_file_path = get_image_file_path_from_image_hash_func(current_image_file_hash)
        current_combined_image_fingerprint_df_row = pd.DataFrame([current_image_file_hash, current_image_file_path]).T
        combined_image_fingerprint_df = combined_image_fingerprint_df.append(current_combined_image_fingerprint_df_row)
    conn.close()
    combined_image_fingerprint_df_vectors = pd.DataFrame()
    for cnt, current_combined_image_fingerprint_vector in enumerate(list_of_combined_image_fingerprint_rows):
        current_combined_image_fingerprint_vector_df = pd.DataFrame(list_of_combined_image_fingerprint_rows[cnt]).T
        combined_image_fingerprint_df_vectors = combined_image_fingerprint_df_vectors.append(current_combined_image_fingerprint_vector_df)
    final_combined_image_fingerprint_df = pd.concat([combined_image_fingerprint_df, combined_image_fingerprint_df_vectors], axis=1)
    return final_combined_image_fingerprint_df
            
def hoeffd_inner_loop_func(i, R, S):
    import numpy as np
    # See slow_exact_hoeffdings_d_func for definition of R, S
    Q_i = 1 + sum(np.logical_and(R<R[i], S<S[i]))
    Q_i = Q_i + (1/4)*(sum(np.logical_and(R==R[i], S==S[i])) - 1)
    Q_i = Q_i + (1/2)*sum(np.logical_and(R==R[i], S<S[i]))
    Q_i = Q_i + (1/2)*sum(np.logical_and(R<R[i], S==S[i]))
    return Q_i

def slow_exact_hoeffdings_d_func(x, y, pool):
    #Based on code from here: https://stackoverflow.com/a/9322657/1006379
    #For background see: https://projecteuclid.org/download/pdf_1/euclid.aoms/1177730150
    x = np.array(x)
    y = np.array(y)
    N = x.shape[0]
    print('Computing tied ranks...')
    with MyTimer():
        R = scipy.stats.rankdata(x, method='average')
        S = scipy.stats.rankdata(y, method='average')
    if 0:
        print('Computing Q with list comprehension...')
        with MyTimer():
            Q = [hoeffd_inner_loop_func(i, R, S) for i in range(N)]
    print('Computing Q with multiprocessing...')
    with MyTimer():
        hoeffd = functools.partial(hoeffd_inner_loop_func, R=R, S=S)
        Q = pool.map(hoeffd, range(N))
    print('Computing helper arrays...')
    with MyTimer():
        Q = np.array(Q)
    D1 = sum(((Q-1)*(Q-2)))
    D2 = sum((R-1)*(R-2)*(S-1)*(S-2))
    D3 = sum((R-2)*(S-2)*(Q-1))
    D = 30*((N-2)*(N-3)*D1 + D2 - 2*(N-2)*D3) / (N*(N-1)*(N-2)*(N-3)*(N-4))
    print('Exact Hoeffding D: '+ str(round(D,8)))
    return D

def generate_bootstrap_sample_func(original_length_of_input, sample_size):
    bootstrap_indices = np.array([random.randint(1,original_length_of_input) for x in range(sample_size)])
    return bootstrap_indices

def compute_average_and_stdev_of_25th_to_75th_percentile_func(input_vector):
    input_vector = np.array(input_vector)
    percentile_25 = np.percentile(input_vector, 25)
    percentile_75 = np.percentile(input_vector, 75)
    trimmed_vector = input_vector[input_vector>percentile_25]
    trimmed_vector = trimmed_vector[trimmed_vector<percentile_75]
    trimmed_vector_avg = np.mean(trimmed_vector)
    trimmed_vector_stdev = np.std(trimmed_vector)
    return trimmed_vector_avg, trimmed_vector_stdev

def compute_average_and_stdev_of_50th_to_90th_percentile_func(input_vector):
    input_vector = np.array(input_vector)
    percentile_50 = np.percentile(input_vector, 50)
    percentile_90 = np.percentile(input_vector, 90)
    trimmed_vector = input_vector[input_vector>percentile_50]
    trimmed_vector = trimmed_vector[trimmed_vector<percentile_90]
    trimmed_vector_avg = np.mean(trimmed_vector)
    trimmed_vector_stdev = np.std(trimmed_vector)
    return trimmed_vector_avg, trimmed_vector_stdev

def compute_bootstrapped_hoeffdings_d_func(x, y, sample_size):
    with ProcessPool(nodes=cpu_count()) as pool:
        x = np.array(x)
        y = np.array(y)
        assert(x.size==y.size)
        original_length_of_input = x.size
        bootstrap_sample_indices = generate_bootstrap_sample_func(original_length_of_input-1, sample_size)
        N = sample_size
        x_bootstrap_sample = x[bootstrap_sample_indices]
        y_bootstrap_sample = y[bootstrap_sample_indices]
        R_bootstrap = scipy.stats.rankdata(x_bootstrap_sample)
        S_bootstrap = scipy.stats.rankdata(y_bootstrap_sample)
        hoeffdingd = functools.partial(hoeffd_inner_loop_func, R=R_bootstrap, S=S_bootstrap)
        Q_bootstrap = pool.imap(hoeffdingd, range(sample_size))
        Q_bootstrap = list(Q_bootstrap)
        Q = np.array(Q_bootstrap)
        D1 = sum(((Q-1)*(Q-2)))
        D2 = sum((R_bootstrap-1)*(R_bootstrap-2)*(S_bootstrap-1)*(S_bootstrap-2))
        D3 = sum((R_bootstrap-2)*(S_bootstrap-2)*(Q-1))
        D = 30*((N-2)*(N-3)*D1 + D2 - 2*(N-2)*D3) / (N*(N-1)*(N-2)*(N-3)*(N-4))
        return D

def compute_parallel_bootstrapped_bagged_hoeffdings_d_func(x, y, sample_size, number_of_bootstraps):
    list_of_Ds = list()
    for ii in range(number_of_bootstraps):
        current_D = compute_bootstrapped_hoeffdings_d_func(x, y, sample_size)
        list_of_Ds.append(current_D)
    robust_average_D, robust_stdev_D = compute_average_and_stdev_of_25th_to_75th_percentile_func(list_of_Ds)
    return robust_average_D

def compute_parallel_bootstrapped_bagged_hoeffdings_d_smaller_sample_size_func(x, y, sample_size, number_of_bootstraps):
    list_of_Ds = list()
    for ii in range(number_of_bootstraps):
        current_D = compute_bootstrapped_hoeffdings_d_func(x, y, sample_size)
        list_of_Ds.append(current_D)
    robust_average_D, robust_stdev_D = compute_average_and_stdev_of_50th_to_90th_percentile_func(list_of_Ds)
    return robust_average_D

def compute_kendalls_tau_func(x_and_y):
    import numpy as np
    from scipy import stats
    x = np.array(x_and_y[0])
    y = np.array(x_and_y[1])
    assert(x.size==y.size)
    kendalltau = stats.kendalltau(x, y).correlation
    return kendalltau

def compute_parallel_bootstrapped_kendalls_tau_func(x, y, sample_size, number_of_bootstraps):
    x = np.array(x)
    y = np.array(y)
    assert(x.size==y.size)
    original_length_of_input = x.size
    list_of_bootstrap_sample_indices = []
    for ii in range(number_of_bootstraps):
        bootstrap_sample_indices = generate_bootstrap_sample_func(original_length_of_input-1, sample_size)
        list_of_bootstrap_sample_indices = list_of_bootstrap_sample_indices + [bootstrap_sample_indices]
    x_bootstraps = []
    y_bootstraps = []
    for current_bootstrap_indices in list_of_bootstrap_sample_indices:
        x_bootstraps = x_bootstraps + [x[current_bootstrap_indices]]
        y_bootstraps = y_bootstraps + [y[current_bootstrap_indices]]
    x_and_y_bootstraps = list(zip(x_bootstraps, y_bootstraps))
    with ProcessPool(nodes=cpu_count()) as pool:
        bootstrapped_kendalltau_results = pool.imap(compute_kendalls_tau_func, x_and_y_bootstraps)
        bootstrapped_kendalltau_results = list(bootstrapped_kendalltau_results)
    bootstrapped_kendalltau_results = [x for x in bootstrapped_kendalltau_results if ~np.isnan(x)]
    robust_average_tau, robust_stdev_tau = compute_average_and_stdev_of_50th_to_90th_percentile_func(bootstrapped_kendalltau_results)
    return robust_average_tau, robust_stdev_tau

def compute_randomized_dependence_func(x_and_y):
    import numpy as np
    from scipy.stats import rankdata
    def calculate_randomized_dependence_coefficient_func(x, y, f=np.sin, k=20, s=1/6., n=1):
        if n > 1:
            values = []
            for i in range(n):
                try:
                    values.append(calculate_randomized_dependence_coefficient_func(x, y, f, k, s, 1))
                except np.linalg.linalg.LinAlgError: pass
            return np.median(values)
        x = np.array(x)
        y = np.array(y)
        if len(x.shape) == 1: x = x.reshape((-1, 1))
        if len(y.shape) == 1: y = y.reshape((-1, 1))
        cx = np.column_stack([rankdata(xc, method='ordinal') for xc in x.T])/float(x.size) # Copula Transformation
        cy = np.column_stack([rankdata(yc, method='ordinal') for yc in y.T])/float(y.size)
        O = np.ones(cx.shape[0])# Add a vector of ones so that w.x + b is just a dot product
        X = np.column_stack([cx, O])
        Y = np.column_stack([cy, O])
        Rx = (s/X.shape[1])*np.random.randn(X.shape[1], k) # Random linear projections
        Ry = (s/Y.shape[1])*np.random.randn(Y.shape[1], k)
        X = np.dot(X, Rx)
        Y = np.dot(Y, Ry)
        fX = f(X) # Apply non-linear function to random projections
        fY = f(Y)
        try:
            C = np.cov(np.hstack([fX, fY]).T) # Compute full covariance matrix
            k0 = k
            lb = 1
            ub = k
            while True: # Compute canonical correlations
                Cxx = C[:int(k), :int(k)]
                Cyy = C[k0:k0+int(k), k0:k0+int(k)]
                Cxy = C[:int(k), k0:k0+int(k)]
                Cyx = C[k0:k0+int(k), :int(k)]
                eigs = np.linalg.eigvals(np.dot(np.dot(np.linalg.inv(Cxx), Cxy), np.dot(np.linalg.inv(Cyy), Cyx)))
                if not (np.all(np.isreal(eigs)) and # Binary search if k is too large
                        0 <= np.min(eigs) and
                        np.max(eigs) <= 1):
                    ub -= 1
                    k = (ub + lb) / 2
                    continue
                if lb == ub: break
                lb = k
                if ub == lb + 1:
                    k = ub
                else:
                    k = (ub + lb) / 2
            return (np.sqrt(np.max(eigs)))**12 #I raise the result to a power since the output is generally so high; this lowers it a bit
        except:
            return 0.0
    x = np.array(x_and_y[0])
    y = np.array(x_and_y[1])
    assert(x.size==y.size)
    randomized_dep = calculate_randomized_dependence_coefficient_func(x,y)
    return randomized_dep

def compute_parallel_bootstrapped_randomized_dependence_func(x, y, sample_size, number_of_bootstraps):
    x = np.array(x)
    y = np.array(y)
    assert(x.size==y.size)
    original_length_of_input = x.size
    list_of_bootstrap_sample_indices = []
    for ii in range(number_of_bootstraps):
        bootstrap_sample_indices = generate_bootstrap_sample_func(original_length_of_input-1, sample_size)
        list_of_bootstrap_sample_indices = list_of_bootstrap_sample_indices + [bootstrap_sample_indices]
    x_bootstraps = []
    y_bootstraps = []
    for current_bootstrap_indices in list_of_bootstrap_sample_indices:
        x_bootstraps = x_bootstraps + [x[current_bootstrap_indices]]
        y_bootstraps = y_bootstraps + [y[current_bootstrap_indices]]
    x_and_y_bootstraps = list(zip(x_bootstraps, y_bootstraps))
    with ProcessPool(nodes=cpu_count()) as pool:
        bootstrapped_randomized_dependence_results = pool.imap(compute_randomized_dependence_func, x_and_y_bootstraps)
        bootstrapped_randomized_dependence_results = list(bootstrapped_randomized_dependence_results)
    bootstrapped_randomized_dependence_results = [x for x in bootstrapped_randomized_dependence_results if ~np.isnan(x)]
    robust_average_randomized_dependence, robust_stdev_randomized_dependence = compute_average_and_stdev_of_50th_to_90th_percentile_func(bootstrapped_randomized_dependence_results)
    return robust_average_randomized_dependence, robust_stdev_randomized_dependence

def get_image_filename_from_registered_image_hash_list_func(registered_image_hash, final_combined_image_fingerprint_df):
    final_combined_image_fingerprint_df_filtered = final_combined_image_fingerprint_df[final_combined_image_fingerprint_df.iloc[:,0]==registered_image_hash]
    corresponding_image_filename = final_combined_image_fingerprint_df_filtered.iloc[:,1].values[0]
    corresponding_image_filename = os.path.split(corresponding_image_filename)[-1]
    return corresponding_image_filename

def get_image_hash_from_registered_image_fingerprint_func(registered_image_fingerprint, final_combined_image_fingerprint_df):
    if 0: #debug:
        final_combined_image_fingerprint_df = get_all_image_fingerprints_from_dupe_detection_database_as_dataframe_func()
        path_to_art_image_file = glob.glob(path_to_all_registered_works_for_dupe_detection+'*')[0]
        registered_image_fingerprint = get_image_deep_learning_features_combined_vector_for_single_image_func(path_to_art_image_file)
    if type(registered_image_fingerprint) == pd.core.frame.DataFrame:
        registered_image_fingerprint__numeric_part = registered_image_fingerprint.iloc[:,2:].values.tolist()[0]
    else:
        registered_image_fingerprint__numeric_part = registered_image_fingerprint
    final_combined_image_fingerprint_df__numeric_part = final_combined_image_fingerprint_df.iloc[:,2:]
    corresponding_index = np.nan
    for indx, current_row in enumerate(final_combined_image_fingerprint_df__numeric_part.iterrows()):
        if current_row[1].tolist() == registered_image_fingerprint__numeric_part:
            corresponding_index = indx
    if corresponding_index == np.nan:
        corresponding_image_hash = np.nan
    else:
        corresponding_image_hash = final_combined_image_fingerprint_df.iloc[corresponding_index,0]
    return corresponding_image_hash

def measure_similarity_of_candidate_image_to_database_func(path_to_art_image_file): 
    pearson__dupe_threshold = 0.995
    spearman__dupe_threshold = 0.79
    kendall__dupe_threshold = 0.70
    randomized_dependence__dupe_threshold = 0.79
    mic__dupe_threshold = 0.70
    hoeffding__dupe_threshold = 0.35
    hoeffding_round2__dupe_threshold = 0.23
    strictness_factor = 0.985
    pearson_max = np.nan
    kendall_max = np.nan
    randomized_dependence_max = np.nan
    mic_max = np.nan
    hoeffding_max = np.nan
    hoeffding_round2_max = np.nan
    
    print('\nChecking if candidate image is a likely duplicate of a previously registered artwork:\n')
    print('Retrieving image fingerprints of previously registered images from local database...')
    with MyTimer():
        final_combined_image_fingerprint_df = get_all_image_fingerprints_from_dupe_detection_database_as_dataframe_func()
        registered_image_fingerprints_transposed_values = final_combined_image_fingerprint_df.iloc[:,2:].T.values
        
    number_of_previously_registered_images_to_compare = len(final_combined_image_fingerprint_df)
    length_of_each_image_fingerprint_vector = len(final_combined_image_fingerprint_df.columns)
    print('Comparing candidate image to the fingerprints of ' + str(number_of_previously_registered_images_to_compare) + ' previously registered images. Each fingerprint consists of ' + str(length_of_each_image_fingerprint_vector) + ' numbers.')
    print('Computing image fingerprint of candidate image...')
    with MyTimer():
        candidate_image_fingerprint = get_image_deep_learning_features_combined_vector_for_single_image_func(path_to_art_image_file)
        candidate_image_fingerprint_transposed_values = candidate_image_fingerprint.iloc[:,2:].T.values.flatten().tolist()

    print("\nComputing Pearson's R, which is fast to compute (We only perform the slower tests on the fingerprints that have a high R).")
    with MyTimer():
        similarity_score_vector__pearson_all = [scipy.stats.pearsonr(candidate_image_fingerprint_transposed_values, registered_image_fingerprints_transposed_values[:,ii])[0] for ii in range(number_of_previously_registered_images_to_compare)]
    pearson_max = np.array(similarity_score_vector__pearson_all).max()
    indices_of_pearson_scores_above_threshold = np.nonzero(np.array(similarity_score_vector__pearson_all) >= strictness_factor*pearson__dupe_threshold)[0].tolist()
    list_of_fingerprints_requiring_further_testing_1 = [registered_image_fingerprints_transposed_values[:,current_index].tolist() for current_index in indices_of_pearson_scores_above_threshold]
    assert(len(list_of_fingerprints_requiring_further_testing_1)==len(indices_of_pearson_scores_above_threshold))
    percentage_of_fingerprints_requiring_further_testing_1 = len(indices_of_pearson_scores_above_threshold)/len(final_combined_image_fingerprint_df)
    print('Selected '+str(len(indices_of_pearson_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_1,2))+'% of the total registered fingerprints).')


    if len(list_of_fingerprints_requiring_further_testing_1) > 0:
        print("Computing Spearman's Rho for selected fingerprints...")
        with MyTimer():
            similarity_score_vector__spearman = [scipy.stats.spearmanr(candidate_image_fingerprint_transposed_values, x).correlation for x in list_of_fingerprints_requiring_further_testing_1]
        spearman_max = np.array(similarity_score_vector__spearman).max()
        if spearman_max >= strictness_factor*spearman__dupe_threshold:
            indices_of_spearman_scores_above_threshold = np.nonzero(np.array(similarity_score_vector__spearman) >= strictness_factor*spearman__dupe_threshold)[0].tolist()
            list_of_fingerprints_requiring_further_testing_2 = [list_of_fingerprints_requiring_further_testing_1[current_index] for current_index in indices_of_spearman_scores_above_threshold]
            assert(len(list_of_fingerprints_requiring_further_testing_2)==len(indices_of_spearman_scores_above_threshold))
            percentage_of_fingerprints_requiring_further_testing_2 = len(indices_of_spearman_scores_above_threshold)/len(final_combined_image_fingerprint_df)
            print('Selected '+str(len(indices_of_spearman_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_2,2))+'% of the total registered fingerprints).')
        else:
            list_of_fingerprints_requiring_further_testing_2 = []
            indices_of_spearman_scores_above_threshold = []
    else:
        list_of_fingerprints_requiring_further_testing_2 = []
        indices_of_spearman_scores_above_threshold = []


    if len(list_of_fingerprints_requiring_further_testing_2) > 0:
        print("Now computing Bootstrapped Kendall's Tau for selected fingerprints...")
        sample_size__kendall = 50
        number_of_bootstraps__kendall = 100
        print("Kendalls's Tau Bootstrap | Sample Size: " + str(sample_size__kendall) + '; Number of Bootstraps: ' + str(number_of_bootstraps__kendall))
        with MyTimer():
            similarity_score_vector__kendall__zipped = [compute_parallel_bootstrapped_kendalls_tau_func(x, candidate_image_fingerprint_transposed_values, sample_size__kendall, number_of_bootstraps__kendall) for x in list_of_fingerprints_requiring_further_testing_2]
        similarity_score_vector__kendall, similarity_score_vector__kendall__stdev = zip(*similarity_score_vector__kendall__zipped)
        similarity_score_vector__kendall__filtered_nans = [1 if x != x else x for x in list(similarity_score_vector__kendall)] 
        #similarity_score_vector__kendall__stdev__filtered_nans =  [1 if x != x else x for x in list(similarity_score_vector__kendall__stdev)]
        stdev_as_pct_of_robust_avg__kendall = np.mean([y/x for x, y in similarity_score_vector__kendall__zipped if np.logical_and(~np.isnan(x), ~np.isnan(y))])
        print('Standard Deviation as % of Average Tau -- average across all fingerprints: ' + str(round(100*stdev_as_pct_of_robust_avg__kendall,2))+'%')
        kendall_max = np.array(similarity_score_vector__kendall__filtered_nans).max()
        if kendall_max >= strictness_factor*kendall__dupe_threshold:
            indices_of_kendall_scores_above_threshold = list(np.nonzero(np.array(similarity_score_vector__kendall__filtered_nans) >= strictness_factor*kendall__dupe_threshold)[0])
            list_of_fingerprints_requiring_further_testing_3 = [list_of_fingerprints_requiring_further_testing_2[current_index] for current_index in indices_of_kendall_scores_above_threshold]
            assert(len(list_of_fingerprints_requiring_further_testing_3)==len(indices_of_kendall_scores_above_threshold))
            percentage_of_fingerprints_requiring_further_testing_3 = len(indices_of_kendall_scores_above_threshold)/len(final_combined_image_fingerprint_df)
            print('Selected '+str(len(indices_of_kendall_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_3,2))+'% of the total registered fingerprints).')
        else:
            list_of_fingerprints_requiring_further_testing_3 = []
            indices_of_kendall_scores_above_threshold = []
    else:
        list_of_fingerprints_requiring_further_testing_3 = []
        indices_of_kendall_scores_above_threshold = []


    if len(list_of_fingerprints_requiring_further_testing_3) > 0:
        print("Now computing Boostrapped Randomized Dependence Coefficient for selected fingerprints...")
        sample_size__randomized_dep = 50
        number_of_bootstraps__randomized_dep = 100
        print("Randomized Dependence Bootstrap | Sample Size: " + str(sample_size__randomized_dep) + '; Number of Bootstraps: ' + str(number_of_bootstraps__randomized_dep))
        with MyTimer():
            similarity_score_vector__randomized_dependence__zipped = [compute_parallel_bootstrapped_randomized_dependence_func(candidate_image_fingerprint_transposed_values, x, sample_size__randomized_dep, number_of_bootstraps__randomized_dep) for x in list_of_fingerprints_requiring_further_testing_3]
        similarity_score_vector__randomized_dependence, similarity_score_vector__randomized_dependence__stdev = zip(*similarity_score_vector__randomized_dependence__zipped)
        similarity_score_vector__randomized_dependence__filtered_nans = [1 if x != x else x for x in list(similarity_score_vector__randomized_dependence)]
        #similarity_score_vector__randomized_dependence__stdev = list(similarity_score_vector__randomized_dependence__stdev)
        stdev_as_pct_of_robust_avg__randomized_dependence = np.mean([y/x for x, y in similarity_score_vector__randomized_dependence__zipped if np.logical_and(~np.isnan(x), ~np.isnan(y))])
        print('Standard Deviation as % of Average Randomized Dependence -- average across all fingerprints: ' + str(round(100*stdev_as_pct_of_robust_avg__randomized_dependence,2))+'%')
        randomized_dependence_max = np.array(similarity_score_vector__randomized_dependence__filtered_nans).max()
        if randomized_dependence_max >= strictness_factor*randomized_dependence__dupe_threshold:
            indices_of_randomized_dependence_scores_above_threshold = list(np.nonzero(np.array(similarity_score_vector__randomized_dependence__filtered_nans) >= strictness_factor*randomized_dependence__dupe_threshold)[0])
            list_of_fingerprints_requiring_further_testing_4 = [list_of_fingerprints_requiring_further_testing_3[current_index] for current_index in indices_of_randomized_dependence_scores_above_threshold]
            assert(len(list_of_fingerprints_requiring_further_testing_4)==len(indices_of_randomized_dependence_scores_above_threshold))
            percentage_of_fingerprints_requiring_further_testing_4 = len(indices_of_randomized_dependence_scores_above_threshold)/len(final_combined_image_fingerprint_df)
            print('Selected '+str(len(indices_of_randomized_dependence_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_4,2))+'% of the total registered fingerprints).')
        else:
            list_of_fingerprints_requiring_further_testing_4 = []
            indices_of_randomized_dependence_scores_above_threshold = []
    else:
        list_of_fingerprints_requiring_further_testing_4 = []
        indices_of_randomized_dependence_scores_above_threshold = []
            
    if len(list_of_fingerprints_requiring_further_testing_4) > 0:
        print("Now computing MIC for selected fingerprints...")
        similarity_score_vector__mic = []
        with MyTimer():
            for current_fingerprint in list_of_fingerprints_requiring_further_testing_4:
                with suppress_stdout_stderr():
                    mine_estimator = minepy.MINE(alpha=0.6, c=15, est="mic_e")
                    mine_estimator.compute_score(candidate_image_fingerprint_transposed_values, current_fingerprint)
                    current_mic_score = mine_estimator.mic()
                    similarity_score_vector__mic.append(current_mic_score)
            mic_max = np.array(similarity_score_vector__mic).max()
        if mic_max >= strictness_factor*mic__dupe_threshold:
            indices_of_mic_scores_above_threshold = list(np.nonzero(np.array(similarity_score_vector__mic) >= strictness_factor*mic__dupe_threshold)[0])
            list_of_fingerprints_requiring_further_testing_5 = [list_of_fingerprints_requiring_further_testing_4[current_index] for current_index in indices_of_mic_scores_above_threshold]
            assert(len(list_of_fingerprints_requiring_further_testing_5)==len(indices_of_mic_scores_above_threshold))
            percentage_of_fingerprints_requiring_further_testing_5 = len(indices_of_mic_scores_above_threshold)/len(final_combined_image_fingerprint_df)
            print('Selected '+str(len(indices_of_mic_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_5,2))+'% of the total registered fingerprints).')
        else:
            list_of_fingerprints_requiring_further_testing_5 = []
            indices_of_mic_scores_above_threshold = []
    else:
        list_of_fingerprints_requiring_further_testing_5 = []
        indices_of_mic_scores_above_threshold = []


    if len(list_of_fingerprints_requiring_further_testing_5) > 0:
        print("Now computing bootstrapped Hoeffding's D for selected fingerprints...")
        sample_size = 20
        number_of_bootstraps = 50
        print('Hoeffding Round 1 | Sample Size: ' + str(sample_size) + '; Number of Bootstraps: ' + str(number_of_bootstraps))
        with MyTimer():
            similarity_score_vector__hoeffding = [compute_parallel_bootstrapped_bagged_hoeffdings_d_smaller_sample_size_func(candidate_image_fingerprint_transposed_values, current_fingerprint, sample_size, number_of_bootstraps) for current_fingerprint in list_of_fingerprints_requiring_further_testing_5]
        hoeffding_max = np.array(similarity_score_vector__hoeffding).max()
        if hoeffding_max >= strictness_factor*hoeffding__dupe_threshold:
            indices_of_hoeffding_scores_above_threshold = list(np.nonzero(np.array(similarity_score_vector__hoeffding) >= strictness_factor*hoeffding__dupe_threshold)[0])
            list_of_fingerprints_requiring_further_testing_6 = [list_of_fingerprints_requiring_further_testing_5[current_index] for current_index in indices_of_hoeffding_scores_above_threshold]
            assert(len(list_of_fingerprints_requiring_further_testing_6)==len(indices_of_hoeffding_scores_above_threshold))
            percentage_of_fingerprints_requiring_further_testing_6 = len(indices_of_hoeffding_scores_above_threshold)/len(final_combined_image_fingerprint_df)
            print('Selected '+str(len(indices_of_hoeffding_scores_above_threshold))+' fingerprints for further testing ('+ str(round(100*percentage_of_fingerprints_requiring_further_testing_6,2))+'% of the total registered fingerprints).')
        else:
            list_of_fingerprints_requiring_further_testing_6 = []
            indices_of_hoeffding_scores_above_threshold = []
    else:
        list_of_fingerprints_requiring_further_testing_6 = []
        indices_of_hoeffding_scores_above_threshold = []


    if len(list_of_fingerprints_requiring_further_testing_6) > 0:
        print("Now computing second round of bootstrapped Hoeffding's D for selected fingerprints using smaller sample size...")
        sample_size__round2 = 75
        number_of_bootstraps__round2 = 20
        print('Hoeffding Round 2 | Sample Size: ' + str(sample_size__round2) + '; Number of Bootstraps: ' + str(number_of_bootstraps__round2))
        with MyTimer():
            similarity_score_vector__hoeffding_round2 = [compute_parallel_bootstrapped_bagged_hoeffdings_d_func(candidate_image_fingerprint_transposed_values, current_fingerprint, sample_size__round2, number_of_bootstraps__round2) for current_fingerprint in list_of_fingerprints_requiring_further_testing_6]
        hoeffding_round2_max = np.array(similarity_score_vector__hoeffding_round2).max()
        if hoeffding_round2_max >= strictness_factor*hoeffding_round2__dupe_threshold:
            indices_of_hoeffding_round2_scores_above_threshold = list(np.nonzero(np.array(similarity_score_vector__hoeffding_round2) >= strictness_factor*hoeffding_round2__dupe_threshold)[0])
            list_of_fingerprints_of_suspected_dupes = [list_of_fingerprints_requiring_further_testing_6[current_index] for current_index in indices_of_hoeffding_round2_scores_above_threshold]
            assert(len(list_of_fingerprints_of_suspected_dupes)==len(indices_of_hoeffding_round2_scores_above_threshold))
        else:
            list_of_fingerprints_of_suspected_dupes = []
            indices_of_hoeffding_round2_scores_above_threshold = []
    else:
        list_of_fingerprints_of_suspected_dupes = []
        indices_of_hoeffding_round2_scores_above_threshold = []

    if len(list_of_fingerprints_of_suspected_dupes) > 0:
       is_likely_dupe = 1
       print('\n\nWARNING! Art image file appears to be a duplicate!')
       index_of_most_similar_fingerprint__spearman = similarity_score_vector__spearman.index(spearman_max)
       fingerprint_of_most_similar_image__spearman = list_of_fingerprints_requiring_further_testing_1[index_of_most_similar_fingerprint__spearman]       
       index_of_most_similar_fingerprint__kendall = similarity_score_vector__kendall__filtered_nans.index(kendall_max)
       fingerprint_of_most_similar_image__kendall = list_of_fingerprints_requiring_further_testing_2[index_of_most_similar_fingerprint__kendall]
       index_of_most_similar_fingerprint__randomized_dependence = similarity_score_vector__randomized_dependence__filtered_nans.index(randomized_dependence_max)
       fingerprint_of_most_similar_image__randomized_dependence = list_of_fingerprints_requiring_further_testing_3[index_of_most_similar_fingerprint__randomized_dependence]       
       index_of_most_similar_fingerprint__mic = similarity_score_vector__mic.index(mic_max)
       fingerprint_of_most_similar_image__mic = list_of_fingerprints_requiring_further_testing_4[index_of_most_similar_fingerprint__mic]    
       index_of_most_similar_fingerprint__hoeffding_round_1 = similarity_score_vector__hoeffding.index(hoeffding_max)
       fingerprint_of_most_similar_image__hoeffding_round_1 = list_of_fingerprints_requiring_further_testing_5[index_of_most_similar_fingerprint__hoeffding_round_1]
       index_of_most_similar_fingerprint__hoeffding_round_2 = similarity_score_vector__hoeffding_round2.index(hoeffding_round2_max)
       fingerprint_of_most_similar_image__hoeffding_round_2 = list_of_fingerprints_requiring_further_testing_6[index_of_most_similar_fingerprint__hoeffding_round_2]
       most_similar_fingerprints_list = [fingerprint_of_most_similar_image__spearman, fingerprint_of_most_similar_image__kendall, fingerprint_of_most_similar_image__randomized_dependence, fingerprint_of_most_similar_image__mic, fingerprint_of_most_similar_image__hoeffding_round_1, fingerprint_of_most_similar_image__hoeffding_round_2]
       most_similar_fingerprints_str_list = [str(fingerprint_of_most_similar_image__spearman), str(fingerprint_of_most_similar_image__kendall), str(fingerprint_of_most_similar_image__randomized_dependence), str(fingerprint_of_most_similar_image__mic), str(fingerprint_of_most_similar_image__hoeffding_round_1), str(fingerprint_of_most_similar_image__hoeffding_round_2)]
       overall_most_similar_fingerprint_str = most_frequently_occurring_element_in_list_func(most_similar_fingerprints_str_list)
       index_of_most_frequently_occurring_fingerprint = most_similar_fingerprints_str_list.index(overall_most_similar_fingerprint_str)
       overall_most_similar_fingerprint = most_similar_fingerprints_list[index_of_most_frequently_occurring_fingerprint]
       print('Candidate Image appears to be a duplicate of the image fingerprint beginning with '+ str(overall_most_similar_fingerprint[0:6]))
       sha_hash_of_similar_registered_image = get_image_hash_from_registered_image_fingerprint_func(overall_most_similar_fingerprint, final_combined_image_fingerprint_df)
       corresponding_filename = get_image_filename_from_registered_image_hash_list_func(sha_hash_of_similar_registered_image, final_combined_image_fingerprint_df)
       print('The SHA256 hash of the registered artwork that is most similar to the candidate image is: '+ sha_hash_of_similar_registered_image)
       print('This image hash corresponds to the filename '+ corresponding_filename)
    else:
       is_likely_dupe = 0

    if not is_likely_dupe:
        print('\n\nArt image file appears to be original! (i.e., not a duplicate of an existing image in the image fingerprint database)')
    column_headers = ['pearson__dupe_threshold', 'spearman__dupe_threshold', 'kendall__dupe_threshold', 'randomized_dependence__dupe_threshold', 'mic__dupe_threshold', 'hoeffding__dupe_threshold', 'hoeffding_round2__dupe_threshold', 'strictness_factor', 'number_of_previously_registered_images_to_compare', 'pearson_max', 'spearman_max', 'kendall_max', 'randomized_dependence_max', 'mic_max', 'hoeffding_max', 'hoeffding_round2_max']
    params_df = pd.DataFrame([pearson__dupe_threshold, spearman__dupe_threshold, kendall__dupe_threshold, randomized_dependence__dupe_threshold, mic__dupe_threshold, hoeffding__dupe_threshold, hoeffding_round2__dupe_threshold, strictness_factor, float(number_of_previously_registered_images_to_compare), pearson_max, spearman_max, kendall_max, randomized_dependence_max, mic_max, hoeffding_max, hoeffding_round2_max]).T
    params_df.columns=column_headers
    params_df = params_df.T
    return is_likely_dupe, params_df
    
def check_suspected_dupe_using_tsne_func(candidate_image_fingerprint, final_combined_image_fingerprint_df):
    if 0:
        with MyTimer():
            final_combined_image_fingerprint_df = get_all_image_fingerprints_from_dupe_detection_database_as_dataframe_func()
        path_to_art_image_file = glob.glob(dupe_detection_test_images_base_folder_path+'*')[0]
        print('Computing image fingerprint of candidate image...')
        with MyTimer():
            candidate_image_fingerprint = get_image_deep_learning_features_combined_vector_for_single_image_func(path_to_art_image_file)
    candidate_image_fingerprint_values = candidate_image_fingerprint.iloc[:,2:].values.flatten()
    registered_image_fingerprints_values = final_combined_image_fingerprint_df.iloc[:,2:].values
    input_for_tsne_embedding = registered_image_fingerprints_values.copy()
    input_for_tsne_embedding = np.concatenate([input_for_tsne_embedding, candidate_image_fingerprint_values[None,:]], axis=0) # the "[:, None]" part casts the vector to an array so the shapes are compatible
    print('Now computing the tSNE embedding of the canidate image together with the set of previously registered image fingerprints...')
    with MyTimer():
        embedded_with_tsne__final_combined_image_fingerprint_df = pd.DataFrame(TSNE(n_components=2).fit_transform(input_for_tsne_embedding))
    embedded_with_tsne__final_combined_image_fingerprint_df.columns = ['X-component', 'Y-component']
    tsne_components_of_existing_registered_fingerprints = embedded_with_tsne__final_combined_image_fingerprint_df.iloc[:-1,:]
    tsne_components_of_candidate_fingerprint = pd.DataFrame(embedded_with_tsne__final_combined_image_fingerprint_df.iloc[-1,:]).T
    list_of_registered_image_hashes = final_combined_image_fingerprint_df.iloc[:,0].tolist()
    tsne_components_of_existing_registered_fingerprints['XY'] = tsne_components_of_existing_registered_fingerprints['X-component'] + tsne_components_of_existing_registered_fingerprints['Y-component']*1j
    tsne_components_of_candidate_fingerprint['XY'] = tsne_components_of_candidate_fingerprint['X-component'] + tsne_components_of_candidate_fingerprint['Y-component']*1j
    list_of_distances = np.abs( (tsne_components_of_existing_registered_fingerprints['XY'].values - tsne_components_of_candidate_fingerprint['XY'].values))
    number_of_closest_fingerprints_to_retrieve = 3
    list_of_indices_of_closest_registered_fingerprints = [x[0] for x in get_indices_of_k_smallest_func(list_of_distances, number_of_closest_fingerprints_to_retrieve)]
    list_of_image_hashes_of_closest_registered_fingerprint = [list_of_registered_image_hashes[x] for x in list_of_indices_of_closest_registered_fingerprints]
    list_of_image_filenames_of_closest_registered_fingerprint = [get_image_filename_from_registered_image_hash_list_func(x, final_combined_image_fingerprint_df) for x in list_of_image_hashes_of_closest_registered_fingerprint]
    return list_of_image_hashes_of_closest_registered_fingerprint, list_of_image_filenames_of_closest_registered_fingerprint

def generate_visualization_of_image_fingerprint_func(path_to_art_image_file):
    print('\nSaving fingerprint visualization')
    nrows, ncols = 130,130
    padding_required = int((nrows*ncols - 16448)/2)
    image_hash = get_image_hash_from_image_file_path_func(path_to_art_image_file)
    df = get_all_image_fingerprints_from_dupe_detection_database_as_dataframe_func()
    df_hashes = list(df.iloc[:,0])
    index_of_hash = [i for i, e in enumerate(df_hashes) if e==image_hash]
    df_values = df.iloc[:,2:].T.values
    candidate_image_fingerprint = df_values[:,index_of_hash].flatten().tolist()
    candidate_image_fingerprint_padded = np.pad(np.array(candidate_image_fingerprint),padding_required,'constant')
    candidate_image_fingerprint_padded_quantiles = [stats.percentileofscore(candidate_image_fingerprint_padded, a, 'rank') for a in candidate_image_fingerprint_padded]
    candidate_image_fingerprint_padded_quantiles_reshaped = np.array(candidate_image_fingerprint_padded_quantiles).reshape(130,130)
    plot = plt.matshow(candidate_image_fingerprint_padded_quantiles_reshaped)
    fig = plot.get_figure()
    output_filename = image_hash + '.png'
    fig.savefig(output_filename, dpi = 300)
    
if 0:
    #For debugging: 
    path_to_art_image_file = glob.glob(dupe_detection_test_images_base_folder_path+'*ORIGINAL*')[0]
    generate_visualization_of_image_fingerprint_func(path_to_art_image_file)


if use_demonstrate_duplicate_detection:
    if __name__ == '__main__':
        freeze_support()
        try:    
            list_of_registered_image_file_hashes = get_list_of_all_registered_image_file_hashes_func()
            print('Found existing image fingerprint database.')
        except:
            print('Generating new image fingerprint database...')
            regenerate_empty_dupe_detection_image_fingerprint_database_func()
            add_all_images_in_folder_to_image_fingerprint_database_func(path_to_all_registered_works_for_dupe_detection)
        
        if 1:
            print('\n\nNow testing duplicate-detection scheme on known near-duplicate images:\n')
            list_of_file_paths_of_near_duplicate_images = glob.glob(dupe_detection_test_images_base_folder_path+'*')
            random_sample_size__near_dupes = 10
            list_of_file_paths_of_near_duplicate_images_random_sample = [list_of_file_paths_of_near_duplicate_images[i] for i in sorted(random.sample(range(len(list_of_file_paths_of_near_duplicate_images)), random_sample_size__near_dupes))]
            list_of_duplicate_check_results__near_dupes = list()
            list_of_duplicate_check_params__near_dupes = list()
            for current_near_dupe_file_path in list_of_file_paths_of_near_duplicate_images_random_sample:
                print('\n________________________________________________________________________________________________________________')
                print('\nCurrent Near Duplicate Image: ' + current_near_dupe_file_path)
                is_likely_dupe, params_df = measure_similarity_of_candidate_image_to_database_func(current_near_dupe_file_path)
                print('\nParameters for current image:')
                print(params_df)
                list_of_duplicate_check_results__near_dupes.append(is_likely_dupe)
                list_of_duplicate_check_params__near_dupes.append(params_df)
            duplicate_detection_accuracy_percentage__near_dupes = sum(list_of_duplicate_check_results__near_dupes)/len(list_of_duplicate_check_results__near_dupes)
            print('________________________________________________________________________________________________________________')
            print('________________________________________________________________________________________________________________')
            print('\nAccuracy Percentage in Detecting Near-Duplicate Images: ' + str(round(100*duplicate_detection_accuracy_percentage__near_dupes,2)) + '%')
            print('________________________________________________________________________________________________________________')
            print('________________________________________________________________________________________________________________')
            
        if 1:
            print('\n\nNow testing duplicate-detection scheme on known non-duplicate images:\n')
            list_of_file_paths_of_non_duplicate_test_images = glob.glob(non_dupe_test_images_base_folder_path+'*')
            random_sample_size__non_dupes = 10
            list_of_file_paths_of_non_duplicate_images_random_sample = [list_of_file_paths_of_non_duplicate_test_images[i] for i in sorted(random.sample(range(len(list_of_file_paths_of_non_duplicate_test_images)), random_sample_size__non_dupes))]
            list_of_duplicate_check_results__non_dupes = list()
            list_of_duplicate_check_params__non_dupes = list()
            for current_non_dupe_file_path in list_of_file_paths_of_non_duplicate_images_random_sample:
                print('\n________________________________________________________________________________________________________________')
                print('\nCurrent Non-Duplicate Test Image: ' + current_non_dupe_file_path)
                is_likely_dupe, params_df = measure_similarity_of_candidate_image_to_database_func(current_non_dupe_file_path)
                print('\nParameters for current image:')
                print(params_df)
                list_of_duplicate_check_results__non_dupes.append(is_likely_dupe)
                list_of_duplicate_check_params__non_dupes.append(params_df)
            duplicate_detection_accuracy_percentage__non_dupes = 1 - sum(list_of_duplicate_check_results__non_dupes)/len(list_of_duplicate_check_results__non_dupes)
            print('________________________________________________________________________________________________________________')
            print('________________________________________________________________________________________________________________')
            print('\nAccuracy Percentage in Detecting Non-Duplicate Images: ' + str(round(100*duplicate_detection_accuracy_percentage__non_dupes,2)) + '%')
            print('________________________________________________________________________________________________________________')
            print('________________________________________________________________________________________________________________')
            
        if 0:
            predicted_y = [i*1 for i in list_of_duplicate_check_results__near_dupes] + [i*1 for i in list_of_duplicate_check_results__non_dupes] 
            actual_y = [1 for x in list_of_duplicate_check_results__near_dupes] + [1 for x in list_of_duplicate_check_results__non_dupes]
            precision, recall, thresholds = sklearn.metrics.precision_recall_curve(actual_y, predicted_y)
            auprc_metric = sklearn.metrics.auc(recall, precision)
            average_precision = sklearn.metrics.average_precision_score(actual_y, predicted_y)
            print('Across all near-duplicate and non-duplicate test images, the Area Under the Precision-Recall Curve (AUPRC) is '+str(round(auprc_metric,3)))
