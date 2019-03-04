import multiprocessing
import io
from collections import OrderedDict

import numpy as np
import pandas as pd
import keras
from keras.applications.imagenet_utils import preprocess_input

from ..settings import NetWorkSettings
from .statistics import calculate_spearmans_rho, calculate_kendalls_tau, calculate_bootstrapped_hoeffdings


NUM_WORKERS = int(round(multiprocessing.cpu_count() / 2))


class _DupeDetector:
    def __init__(self):
        self.DUPE_DETECTION_MODELS = OrderedDict()

        for modelname in NetWorkSettings.DUPE_DETECTION_MODELS:
            if modelname == "VGG16":
                self.DUPE_DETECTION_MODELS['VGG16'] = keras.applications.vgg16.VGG16(weights='imagenet', include_top=False, pooling='avg')
            elif modelname == "Xception":
                self.DUPE_DETECTION_MODELS['Xception'] = keras.applications.xception.Xception(weights='imagenet', include_top=False, pooling='avg')
            elif modelname == "InceptionResNetV2":
                self.DUPE_DETECTION_MODELS['InceptionResNetV2'] = keras.applications.inception_resnet_v2.InceptionResNetV2(weights='imagenet', include_top=False, pooling='avg')
            elif modelname == "DenseNet201":
                self.DUPE_DETECTION_MODELS['DenseNet201'] = keras.applications.DenseNet201(weights='imagenet', include_top=False, pooling='avg')
            elif modelname == "InceptionV3":
                self.DUPE_DETECTION_MODELS['InceptionV3'] = keras.applications.inception_v3.InceptionV3(weights='imagenet', include_top=False, pooling='avg')
            else:
                raise ValueError("Invalid dupe detection model name in settings: %s" % modelname)

    def __prepare_fingerprint_for_export(self, image_feature_data):
        image_feature_data_arr = np.char.mod('%f', image_feature_data)  # convert from Numpy to a list of values
        # convert image data to float64 matrix. float64 is need for bh_sne
        x_data = np.asarray(image_feature_data_arr).astype('float64')
        image_fingerprint_vector = x_data.reshape((x_data.shape[0], -1))
        return image_fingerprint_vector

    def compute_deep_learning_features(self, data):
        # read the actual image file
        imagefile = io.BytesIO(data)

        # load image
        image = keras.preprocessing.image.load_img(imagefile, target_size=NetWorkSettings.DUPE_DETECTION_TARGET_SIZE)

        # the image is now in an array of shape (3, 224, 224) but we need to expand it to (1, 2, 224, 224) as
        # Keras is expecting a list of images
        x = keras.preprocessing.image.img_to_array(image)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        fingerprint_dict = {}
        for k, v in self.DUPE_DETECTION_MODELS.items():
            features = v.predict(x)[0]  # extract the features
            fingerprint_vector = self.__prepare_fingerprint_for_export(features)
            fingerprint_dict[k] = fingerprint_vector

        fingerprints = []
        for k, v in fingerprint_dict.items():
            # REFACTOR: we inherited this interface
            value_flattened = [x[0] for x in v.tolist()]
            fingerprints += value_flattened

        return fingerprints


def measure_similarity(combined_fingerprint, fingerprint_table):
    spearman_thresh = NetWorkSettings.DUPE_DETECTION_SPEARMAN_THRESHOLD
    kendall_thresh = NetWorkSettings.DUPE_DETECTION_KENDALL_THRESHOLD
    hoeffding_thresh = NetWorkSettings.DUPE_DETECTION_HOEFFDING_THRESHOLD
    strictness = NetWorkSettings.DUPE_DETECTION_STRICTNESS
    kendall_max = NetWorkSettings.DUPE_DETECTION_KENDALL_MAX
    hoeffding_max = NetWorkSettings.DUPE_DETECTION_HOEFFDING_MAX

    is_duplicate = False

    # prepare combined_fingerprint
    A = pd.DataFrame(["DUMMY_HASH", "DUMMY_PATH"]).T        # TODO: fill these properly?
    B = pd.DataFrame(combined_fingerprint)
    combined_image_fingerprint_df_row = pd.concat([A, B], axis=1, join_axes=[A.index])
    candidate_fingerprint = combined_image_fingerprint_df_row.iloc[:, 2:].T.values.flatten().tolist()
    # end

    print('Checking if candidate image is a likely duplicate of a previously registered artwork:')

    registered_fingerprints = fingerprint_table.iloc[:, 2:].T.values
    print('Comparing candidate image to the fingerprints of %s previously registered images.' % len(fingerprint_table))
    print('Each fingerprint consists of %s numbers.' % len(fingerprint_table.columns))

    # Computing Spearman's Rho, which is fast to compute. We only perform the
    # slower tests on the fingerprints that have a high Rho
    spearman_vector, spearman_max, requires_kendalls = calculate_spearmans_rho(candidate_fingerprint,
                                                                               fingerprint_table,
                                                                               registered_fingerprints,
                                                                               strictness,
                                                                               spearman_thresh)
    print("Computed Spearman's Rho", spearman_max)

    # do we need to calculate Kendall's?
    if len(requires_kendalls) > 0:
        print("Computing Kendall's Tau")
        requires_hoeffdings = calculate_kendalls_tau(candidate_fingerprint, requires_kendalls, strictness, kendall_thresh)

        # do we need to calculate hoeffdings?
        if len(requires_hoeffdings) > 0:
            print("Computing Bootstrapped Hoeffding's")
            duplicates = calculate_bootstrapped_hoeffdings(candidate_fingerprint, spearman_vector, requires_hoeffdings,
                                                           strictness, hoeffding_thresh, NUM_WORKERS)

            # it seems we have found a duplicate
            if len(duplicates):
                is_duplicate = True

                print('WARNING! Art image file appears to be a duplicate!')
                print('Candidate appears to be a duplicate of the image fingerprint beginning with %s' % duplicates[0][0:5])

                for ii in range(len(fingerprint_table)):
                    current_fingerprint = registered_fingerprints[:, ii].tolist()
                    if current_fingerprint == duplicates[0]:
                        shahash = fingerprint_table.iloc[ii, 0]
                        print('The SHA256 hash of the registered artwork that is similar to the candidate image: ' + shahash)

    # assemble parameters
    column_headers = ['spearman_thresh', 'kendall_thresh', 'hoeffding_thresh',
                      'strictness', 'fingerprint_db_size', 'spearman_max',
                      'kendall_max', 'hoeffding_max']
    params_df = pd.DataFrame([spearman_thresh, kendall_thresh, hoeffding_thresh, strictness,
                              float(len(fingerprint_table)), spearman_max, kendall_max, hoeffding_max]).T
    params_df.columns = column_headers
    params_df = params_df.T

    return is_duplicate, params_df


def assemble_fingerprints_for_pandas(db):
    df_vectors = pd.DataFrame()
    pandas_fingerprint_table = pd.DataFrame()

    for current_image_file_hash, data in db:
        file_path, combined = data

        df_vectors = df_vectors.append(combined)

        # create dataframe rows for every image
        df_row = pd.DataFrame([current_image_file_hash, file_path]).T
        pandas_fingerprint_table = pandas_fingerprint_table.append(df_row)

    final_pandas_table = pd.concat([pandas_fingerprint_table, df_vectors], axis=1,
                                   join_axes=[pandas_fingerprint_table.index])
    return final_pandas_table


# dupe detector singleton that loads __DupeDetector lazily as the models are extremely large
class DupeDetector:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if class_._instance is None:
            class_._instance = _DupeDetector()
        return class_._instance
