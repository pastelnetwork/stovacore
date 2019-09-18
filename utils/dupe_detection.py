import io
from collections import OrderedDict

import numpy as np
import keras
from keras.applications.imagenet_utils import preprocess_input


class _DupeDetector:
    def __init__(self, dupe_detection_models, dupe_detection_target_size):
        self.dupe_detection_target_size = dupe_detection_target_size
        self.DUPE_DETECTION_MODELS = OrderedDict()

        for modelname in dupe_detection_models:
            if modelname == "VGG16":
                self.DUPE_DETECTION_MODELS['VGG16'] = keras.applications.vgg16.VGG16(weights='imagenet',
                                                                                     include_top=False, pooling='avg')
            elif modelname == "Xception":
                self.DUPE_DETECTION_MODELS['Xception'] = keras.applications.xception.Xception(weights='imagenet',
                                                                                              include_top=False,
                                                                                              pooling='avg')
            elif modelname == "InceptionResNetV2":
                self.DUPE_DETECTION_MODELS[
                    'InceptionResNetV2'] = keras.applications.inception_resnet_v2.InceptionResNetV2(weights='imagenet',
                                                                                                    include_top=False,
                                                                                                    pooling='avg')
            elif modelname == "DenseNet201":
                self.DUPE_DETECTION_MODELS['DenseNet201'] = keras.applications.DenseNet201(weights='imagenet',
                                                                                           include_top=False,
                                                                                           pooling='avg')
            elif modelname == "InceptionV3":
                self.DUPE_DETECTION_MODELS['InceptionV3'] = keras.applications.inception_v3.InceptionV3(
                    weights='imagenet', include_top=False, pooling='avg')
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
        image = keras.preprocessing.image.load_img(imagefile, target_size=self.dupe_detection_target_size)

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


# dupe detector singleton that loads __DupeDetector lazily as the models are extremely large
class DupeDetector:
    _instance = None

    def __new__(class_, *args, **kwargs):
        if class_._instance is None:
            class_._instance = _DupeDetector(*args, **kwargs)
        return class_._instance
