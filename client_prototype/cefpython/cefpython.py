from cefpython3 import cefpython as cef
import platform
import sys

from core_modules.helpers import require_true


def start_cefpython(windowtitle, url):
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    cef.Initialize()
    cef.CreateBrowserSync(url=url,
                          window_title=windowtitle)
    cef.MessageLoop()
    cef.Shutdown()


def check_versions():
    ver = cef.GetVersion()
    print("[hello_world.py] CEF Python {ver}".format(ver=ver["version"]))
    print("[hello_world.py] Chromium {ver}".format(ver=ver["chrome_version"]))
    print("[hello_world.py] CEF {ver}".format(ver=ver["cef_version"]))
    print("[hello_world.py] Python {ver} {arch}".format(
           ver=platform.python_version(),
           arch=platform.architecture()[0]))
    require_true(cef.__version__ >= "57.0", msg="CEF Python v57.0+ required to run this")


if __name__ == '__main__':
    start_cefpython("google.com", "https://google.com")
