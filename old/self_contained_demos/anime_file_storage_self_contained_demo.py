import sys
import tarfile
import urllib


from file_storage_module.helpers import get_sha256_hash_of_input_data_func
from file_storage_module.stress_testing import *
from file_storage_module.compression import decompress_data_with_zstd_func
from masternode_protype.masternode_modules.animecoin_modules.luby import encode_file_into_luby_blocks_func, reconstruct_data_from_luby_blocks


# Note: Code is based on the Python LT implementation by Anson Rosenthal, found here: https://github.com/anrosent/LT-code

# Parameters:
use_demonstrate_luby_blocks = 1
block_redundancy_factor = 12  # How many times more blocks should we store than are required to regenerate the file?
desired_block_size_in_bytes = 1024 * 1000 * 2
root_animecoin_folder_path = '/home/synapse/tmp/animecoin/'
prepared_final_art_zipfiles_folder_path = os.path.join(root_animecoin_folder_path, 'prepared_final_art_files' + os.sep)
test_art_file_name = 'Arturo_Lopez__Number_03'
folder_containing_art_image_and_metadata_files = root_animecoin_folder_path + 'art_folders_to_encode' + os.sep + test_art_file_name + os.sep
path_to_folder_containing_luby_blocks = root_animecoin_folder_path + 'block_files' + os.sep
path_to_save_reconstructed_and_decompressed_files = root_animecoin_folder_path + 'reconstructed_files' + os.sep + test_art_file_name + os.sep
percentage_of_block_files_to_randomly_delete = 0.65
percentage_of_block_files_to_randomly_corrupt = 0.10
percentage_of_each_selected_file_to_be_randomly_corrupted = 0.02
art_block_storage_folder_path = root_animecoin_folder_path + 'art_block_storage'



def save_reconstructed_data_to_file_and_decompress_func(reconstructed_data,
                                                        path_to_save_reconstructed_and_decompressed_files):
    decompressed_reconstructed_data = decompress_data_with_zstd_func(reconstructed_data)
    if not os.path.isdir(path_to_save_reconstructed_and_decompressed_files):
        os.makedirs(path_to_save_reconstructed_and_decompressed_files)
    with open(path_to_save_reconstructed_and_decompressed_files + 'art_files.tar', 'wb') as f:
        f.write(decompressed_reconstructed_data)
    with tarfile.open(path_to_save_reconstructed_and_decompressed_files + 'art_files.tar') as tar:
        tar.extractall(path=path_to_save_reconstructed_and_decompressed_files)
    try:
        os.remove(path_to_save_reconstructed_and_decompressed_files + 'art_files.tar')
    except Exception as e:
        print('Error: ' + str(e))


def get_block_file_list_from_masternode_func(ip_address_of_masternode):
    masternode_file_server_url = 'http://' + ip_address_of_masternode + '/'
    response = urllib.request.urlopen(masternode_file_server_url)
    response_html_string = response.read()
    response_html_string_split = response_html_string.decode('utf-8').split('./')
    list_of_available_block_file_names = [x.split('</a><br>')[0] for x in response_html_string_split if
                                          'FileHash__' in x]
    list_of_available_art_file_hashes = list(
        set([x.split('FileHash__')[1].split('__Block__')[0] for x in list_of_available_block_file_names]))
    list_of_available_block_file_hashes = list(
        set([x.split('__BlockHash_')[1].split('.block')[0] for x in list_of_available_block_file_names]))
    return list_of_available_block_file_names, list_of_available_art_file_hashes, list_of_available_block_file_hashes


def get_local_matching_blocks_from_art_file_hash_func(art_block_storage_folder_path, sha256_hash_of_desired_art_file=''):
    list_of_block_file_paths = glob.glob(
        os.path.join(art_block_storage_folder_path, '*' + sha256_hash_of_desired_art_file + '*.block'))
    list_of_block_hashes = []
    list_of_file_hashes = []
    for current_block_file_path in list_of_block_file_paths:
        reported_file_sha256_hash = current_block_file_path.split('\\')[-1].split('__')[1]
        list_of_file_hashes.append(reported_file_sha256_hash)
        reported_block_file_sha256_hash = current_block_file_path.split('__')[-1].replace('.block', '').replace(
            'BlockHash_', '')
        list_of_block_hashes.append(reported_block_file_sha256_hash)
    return list_of_block_file_paths, list_of_block_hashes, list_of_file_hashes


def get_all_local_block_file_hashes_func(art_block_storage_folder_path):
    _, list_of_block_hashes, list_of_art_file_hashes = get_local_matching_blocks_from_art_file_hash_func(art_block_storage_folder_path)
    list_of_block_hashes = list(set(list_of_block_hashes))
    list_of_art_file_hashes = list(set(list_of_art_file_hashes))
    return list_of_art_file_hashes, list_of_block_hashes


def get_local_block_file_binary_data_func(block_storage_folder_path, sha256_hash_of_desired_block):
    list_of_block_file_paths = glob.glob(
        os.path.join(art_block_storage_folder_path, '*' + sha256_hash_of_desired_block + '*.block'))
    try:
        with open(list_of_block_file_paths[0], 'rb') as f:
            block_binary_data = f.read()
            return block_binary_data
    except Exception as e:
        print('Error: ' + str(e))


def create_storage_challenge_func(block_storage_folder_path, ip_address_of_masternode):
    # ip_address_of_masternode = '149.28.34.59'
    _, _, list_of_remote_block_file_hashes = get_block_file_list_from_masternode_func(ip_address_of_masternode)
    _, list_of_local_block_file_hashes = get_all_local_block_file_hashes_func(art_block_storage_folder_path)
    list_of_block_files_available_remotely_and_locally = list(
        set(list_of_remote_block_file_hashes) & set(list_of_local_block_file_hashes))
    randomly_selected_block_file_hash_for_challenge = random.choice(list_of_block_files_available_remotely_and_locally)
    block_binary_data = get_local_block_file_binary_data_func(block_storage_folder_path, randomly_selected_block_file_hash_for_challenge)
    size_of_block_file_in_bytes = sys.getsizeof(block_binary_data)
    challenge_start_byte = random.randint(0, size_of_block_file_in_bytes)
    challenge_end_byte = random.randint(0, size_of_block_file_in_bytes)
    if challenge_start_byte > challenge_end_byte:
        tmp = challenge_end_byte
        challenge_end_byte = challenge_start_byte
        challenge_start_byte = tmp
    block_binary_data_random_segment = block_binary_data[challenge_start_byte:challenge_end_byte]
    size_of_block_file_random_segment_in_bytes = sys.getsizeof(block_binary_data_random_segment)
    assert (size_of_block_file_random_segment_in_bytes != 0)
    sha256_hash_of_block_file_random_segment = get_sha256_hash_of_input_data_func(block_binary_data_random_segment)
    return randomly_selected_block_file_hash_for_challenge, challenge_start_byte, challenge_end_byte, sha256_hash_of_block_file_random_segment


if use_demonstrate_luby_blocks:
    print("folder_containing_art_image_and_metadata_files:", folder_containing_art_image_and_metadata_files)
    print("path_to_folder_containing_luby_blocks:", path_to_folder_containing_luby_blocks)
    print("path_to_save_reconstructed_and_decompressed_files:", path_to_save_reconstructed_and_decompressed_files)

    duration_in_seconds = encode_file_into_luby_blocks_func(block_redundancy_factor, desired_block_size_in_bytes,
                                                            folder_containing_art_image_and_metadata_files,
                                                            path_to_folder_containing_luby_blocks)

    number_of_deleted_blocks = delete_percentage_of_blocks(
        path_to_folder_containing_luby_blocks, percentage_of_block_files_to_randomly_delete)

    number_of_corrupted_blocks = corrupt_percentage_of_blocks(
        path_to_folder_containing_luby_blocks, percentage_of_block_files_to_randomly_corrupt,
        percentage_of_each_selected_file_to_be_randomly_corrupted)

    reconstructed_data = reconstruct_data_from_luby_blocks(path_to_folder_containing_luby_blocks)

    save_reconstructed_data_to_file_and_decompress_func(reconstructed_data,
                                                        path_to_save_reconstructed_and_decompressed_files)
