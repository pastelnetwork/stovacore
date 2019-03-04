import shutil
import subprocess
import os

BASEDIR = os.path.abspath(os.path.join(__file__, "..", ".."))
ANIMECOIND_DIR = os.path.dirname(os.path.dirname(BASEDIR))
BUILDROOT = os.path.join(BASEDIR, "buildscripts", "tmp")
VIRTUAL_ENV = os.environ.get("VIRTUAL_ENV")

DISTDIR = os.path.join(BUILDROOT, "dist")
BUILDDIR = os.path.join(BUILDROOT, "build")
SPECDIR = os.path.join(BUILDROOT, "spec")
FINALDIR = os.path.join(BUILDROOT, "final")


class Builder:
    def __init__(self):
        if VIRTUAL_ENV is None:
            print("You have to run the script from the virtual environment that contains the packages!")
            exit(-1)

    def __clean_buildroot(self):
        print("[+] Cleaning buildroot")
        shutil.rmtree(BUILDROOT, ignore_errors=True)

    def __call_pyinstaller(self, target, extra_data=None, name=None, envparam=None, cwdparam=None, extra_paths=None):
        if cwdparam is None:
            cwd = BASEDIR
        else:
            cwd = cwdparam

        env = os.environ
        if envparam is not None:
            for k, v in envparam.items():
                env[k] = v

        # target is a filename without the extension: test.py -> test

        print("[+] Building target: %s, cwd: %s" % (target, cwd))

        cmdline = [
            "pyinstaller",
            "--distpath", DISTDIR,
            "--workpath", BUILDDIR,
            "--specpath", SPECDIR,
            "--paths", BASEDIR,
            "--noconfirm",
            #"--clean"
        ]

        # do we need extra paths?
        if extra_paths is not None:
            for path in extra_paths:
                cmdline.append("--paths")
                cmdline.append(path)

        # if extra data is set, append them
        if extra_data is not None:
            for data in extra_data:
                cmdline.append("--add-data")
                cmdline.append(data)

        # if name is set, append it
        if name is not None:
            cmdline.append("--name")
            cmdline.append(name)
        else:
            name = target

        print("[+] Creating spec file for %s" % target)
        p = subprocess.Popen(cmdline + ["%s.py" % target], env=env, cwd=cwd)
        if p.wait() != 0:
            raise ValueError("Return code is not zero!")

        print("[+] Building spec file for %s" % target)
        p = subprocess.Popen(cmdline + ["%s/%s.spec" % (SPECDIR, name)], env=env, cwd=cwd)
        p.wait()
        if p.wait() != 0:
            raise ValueError("Return code is not zero!")

    def __merge_built_directories(self):
        # NOTE: Since pyinstaller is garbage and the merge feature is broken for years now in the 3.0 version
        #       we have to resort to this. The only real drawback is that the compiled executables will include
        #       duplicated core code, but this couple extra MBs won't cause much harm.

        print("[+] Making final directory")
        os.makedirs(FINALDIR)

        print("[+] Assembling final archive")
        for distdirname in os.listdir(DISTDIR):
            distdir = os.path.join(DISTDIR, distdirname)
            print("[+] Found build dir %s" % distdir)

            for root, dirs, files in os.walk(distdir):
                # print(root, dirs, files)
                for filename in files:
                    # get the full path to filename
                    srcpath = os.path.join(root, filename)

                    # get the relative path to distdir
                    relpath = srcpath.replace(distdir + "/", "")

                    # get the target name of the file
                    dstpath = os.path.join(FINALDIR, relpath)

                    # create directory if it does not exist
                    os.makedirs(os.path.dirname(dstpath), exist_ok=True)

                    # check if we are about to overwrite something with a different file size
                    if os.path.exists(dstpath):
                        srcstat = os.stat(srcpath)
                        dststat = os.stat(dstpath)
                        if srcstat.st_size != dststat.st_size:
                            msg = "[-] Error dstfile exists and sizes don't match!'\n\tsrc:%s\n\tdst:%s" % (
                                srcpath, dstpath)
                            print(msg)
                            raise ValueError(msg)
                        else:
                            # sizes are the same, so we assume it's the same file
                            continue

                    shutil.copy2(srcpath, dstpath)

    def build(self):
        print(("[+] Starting build process with:\n\tBASEDIR: %s\n\t" +
               "BUILDROOT: %s\n\tVIRTUAL_ENV: %s\n\tANIMECOIND_DIR: %s") % (
                   BASEDIR, BUILDROOT, VIRTUAL_ENV, ANIMECOIND_DIR))

        self.__clean_buildroot()

        self.__call_pyinstaller("run_all_unittests")

        # NOTE: extra data is relative to BASEDIR, as that's the default cwd for pyinstaller
        self.__call_pyinstaller("start_single_masternode", extra_data=[
                    "%s/misc/nsfw_trained_model.pb:misc/" % BASEDIR,
                    "%s/../../../animecoin_blockchain/AnimeCoin/src/animecoind:animecoind/" % BASEDIR])

        # TODO: this does not place the chroot_dir in the resulting artifact
        self.__call_pyinstaller("parse_image_in_jail", extra_data=["%s/chroot_dir:chroot_dir/" % BASEDIR])

        DJANGO_ROOT = os.path.join(BASEDIR, "client_prototype", "django_frontend")
        self.__call_pyinstaller("start_django",
                                envparam={
                                    "DJANGO_SETTINGS_MODULE": "client_prototype/django_frontend/frontend/settings.py",
                                    "PASTEL_BASEDIR": "/tmp/nonexistentthisisjustadummydir/node0",
                                    "PASTEL_RPC_IP": "0.0.0.0",
                                    "PASTEL_RPC_PORT": "12345",
                                    "PASTEL_RPC_PUBKEY": "dGVzdA==",
                                },
                                extra_data=[
                                    "%s/client_prototype/django_frontend/core/templates:core/templates/" % BASEDIR,
                                    "%s/client_prototype/django_frontend/static:static/" % BASEDIR,
                                ],
                                cwdparam=DJANGO_ROOT,
                                extra_paths=[DJANGO_ROOT],
                                name="start_django")

        self.__merge_built_directories()


if __name__ == "__main__":
    builder = Builder()
    builder.build()
