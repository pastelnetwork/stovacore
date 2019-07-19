import subprocess

from core_modules.logger import initlogging
from core_modules.settings import NetWorkSettings


class JailedImageParser:
    def __init__(self, nodenum, file_data):
        self.__logger = initlogging('', __name__)

        if len(file_data) > NetWorkSettings.IMAGE_MAX_SIZE:
            raise ValueError("File is larger than NetWorkSettings.IMAGE_MAX_SIZE (%s)" % NetWorkSettings.IMAGE_MAX_SIZE)

        self.file_data = file_data

    def parse(self):
        # make sure original file and resulting file are exact matches, careful not to allow a DoS by memory consumption

        try:
            output = self.__call_jailed_converter()
        except Exception as exc:
            self.__logger.exception("Exception occured in jailed converter: %s" % exc)
            raise

        if output != self.file_data:
            raise RuntimeError("Output differs from input!")

        self.__logger.debug("Output file is validated successfully")

    def __call_jailed_converter(self):
        # make this use popen
        process = subprocess.Popen(NetWorkSettings.IMAGEPARSERCMDLINE, bufsize=0, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, close_fds=True, shell=False)
        outbuf, errbuf = b'', b''
        # start = dt.now()
        while process.poll() is None:
            # TODO: time out subprocess after X seconds
            # now = dt.now()
            # delta = (now-start).total_seconds()
            # if delta > NetWorkSettings.IMAGE_PARSER_TIMEOUT_SECONDS:
            #     raise RuntimeError("Image parser took longer than %s: %s" % (
            #         NetWorkSettings.IMAGE_PARSER_TIMEOUT_SECONDS, delta))

            # TODO: this can DoS us, since async communication is not possible and direct reading/writing from
            # process.stdout/stderr can result in deadlocks according to the documentation.

            stdoutdata, stderrdata = process.communicate(input=self.file_data)
            outbuf += stdoutdata
            errbuf += stderrdata

        retval = process.poll()
        if retval != 0:
            self.__logger.debug("Process terminated with bad retval: %s" % retval)
            self.__logger.debug("STDERR of jailed process: %s" % errbuf.decode("utf-8"))
            raise RuntimeError("Process terminated with non-zero return value!")

        return outbuf
