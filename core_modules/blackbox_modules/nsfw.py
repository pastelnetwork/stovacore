import tensorflow as tf
from core_modules.settings import NetWorkSettings


class __NSFWDetector:
    def __init__(self):
        with tf.gfile.FastGFile(NetWorkSettings.NSFW_MODEL_FILE, 'rb') as f:  # Unpersists graph from file
            self.__nsfw_graph = tf.GraphDef()
            self.__nsfw_graph.ParseFromString(f.read())
        tf.import_graph_def(self.__nsfw_graph, name='')

    def get_score(self, image_data):
        with tf.Session() as sess:
            # Feed the image_data as input to the graph and get first prediction
            softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
            # TODO: does this only work for jpegs?
            predictions = sess.run(softmax_tensor,  {'DecodeJpeg/contents:0': image_data})

            # Sort to show labels of first prediction in order of confidence
            top_k = predictions[0].argsort()[-len(predictions[0]):][::-1]
            for graph_node_id in top_k:
                image_sfw_score = predictions[0][graph_node_id]
            image_nsfw_score = 1 - image_sfw_score

            return image_nsfw_score

    def is_nsfw(self, image_data):
        return self.get_score(image_data) > NetWorkSettings.NSFW_THRESHOLD


# create an instance of this to be used globally
NSFWDetector = __NSFWDetector()
