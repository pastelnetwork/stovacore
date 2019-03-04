import sys

from core_modules.jailed_image_parser import JailedImageParser


if __name__ == "__main__":
    # TODO turn this into a unit test
    filename = sys.argv[1]
    image_data = open(filename, "rb").read()
    converter = JailedImageParser(0, image_data)
    converter.parse()
