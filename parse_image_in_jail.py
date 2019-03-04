import sys
import os
import io

from core_modules.settings import NetWorkSettings

from cgroupspy import trees
import prctl

from PIL import Image


### SECURITY NOTES ###
#  CURRENT STATUS
#    This is the command we need to this program with is:
#      unshare -mUuinpCrf --mount-proc=/proc
#
#    We want the image converter to be in python, so we have to be able to load stuff from the same virtualenv
#    as the non-jailed process is running. We achieve this by loading everything we need at the start, the we drop
#    all of our privileges, restrict ourselves to a limited environment and only then invoking the actual conversion
#    function. We must never do anything risky while we hold the privileges.
#
#    To do anything malicious the attacker would have to blindly and remotely exploit a png parse bug. This is made
#    borderline impossible by the following:
#
#  COUNTERMEASURES
#
#      1) ASLR (Address Space Layout Randomization) - implemented by the OS (tested on Ubuntu 17.10)
#      2) NX (W^X, no writable address is executable) - implemented by the OS (tested on Ubuntu 17.10)
#      3) Linux namespaces - implemented fully
#      4) Dropping capabilities and no_new_privs - implemented
#      5) Linux cgroups - not implemented
#      6) extra countermeasures - not implemented
#
#    1+2) ASLR and NX
#      Examine with: python -c "print(open('/proc/self/maps').read())"
#
#      On Ubuntu 17.10 this yields proper randomization, except for:
#          009be000-009bf000 r--p 003be000 fd:01 6038165                   /home/user/.virtualenvs/AnimeCoin/bin/python
#          009bf000-00a5b000 rw-p 003bf000 fd:01 6038165                   /home/user/.virtualenvs/AnimeCoin/bin/python
#          00a5b000-00a8d000 rw-p 00000000 00:00 0
#          ffffffffff600000-ffffffffff601000 r-xp 00000000 00:00 0         [vsyscall]
#
#     TODO: on running system we need to disable the vsyscall section to prevent ROP gadgets in this section
#
#      Every other section is randomized between runs, and no section is both writable and executable. This means that
#      as long as we ensure that proper randomization occurs (exec this binary, do not use fork()!), we can be sure
#      that blind exploitation is extremely unlikely.
#
#    3) Linux namespaces
#      With unshare we can restrict the image converter using the following namespaces, however because unshare is
#      a very limited utility, some of these don't work how we want to
#        o mount - RESTRICTED - we can't interfere with mounts
#                               We are using chroots instead of new mounts to restrict access (chroot to an empty dir).
#                               We could also restrict file access with mount --rbind -o nosuid,nodev,ro if
#                               we ever need to see the entire filesystem. However, then we have to prevent the keys
#                               from being read as we are running as the user outside the container.
#        o uts - RESTRICTED
#        o ipc - RESTRICTED
#        o net - RESTRICTED - no network access, not even 127.0.0.1
#        o pid - RESTRICTED - no processes can be talked to outside namespace, even though our outside uid is the same
#        o user - RESTRICTED - we run as uid 0 in the container to be able to chroot, but
#                              our effective uid outside is our user id
#        o cgroup - not used
#
#    4) Dropping all capabilities
#      All capabilities are dropped using prctl and we prevent new ones from being acquired through suids using
#      no_new_privs.
#
#    5) Linux cgroups
#      Cgroup limitation is not done at all yet. cgroupspy, however can be used for this purpose.
#
#    6) Extra countermeasures
#      b) Close open file descriptors to limit attack surface, prevent chroot escapes, etc...
#      c) Limit system calls accessible with seccomp to reduce kernel attack surface,
#         an image converter probably only needs to read and write files, possibly mmap
#      d) Monitoring: report failed invocations of the image converter and detect anomalies
#         we need to prevent attackers from hammering this interface with requests, as the defenses are probabilistic
#
#  FUTURE WORK
#    DDoS mitigation is an unsolved issue right now, we need to limit available resources using cgroups.
### END ###


class ImageParse:
    def __init__(self):
        # TODO: UGLY HACK
        # We load our 1x1px sample png to circumvent PIL's lazy loading. If we let it lazy load it will fail, since
        # the final application will be inside an empty chroot.
        self.image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00' \
                          b'%\xdbV\xca\x00\x00\x00\x03PLTE\xffM\x00\\58\x7f\x00\x00\x00\x01tRNS\xcc\xd24V\xfd\x00\x00' \
                          b'\x00\nIDATx\x9ccb\x00\x00\x00\x06\x00\x0367|\xa8\x00\x00\x00\x00IEND\xaeB`\x82'
        Image.open(io.BytesIO(initial_bytes=self.image_data))

        # set up cgroups
        # TODO: we can set cgroups to limit the resources the child process can use
        tree = trees.Tree()
        for children in tree.root.children:
            name = children.name
            node = tree.get_node_by_path(children.path)

            if name == b'cpuset':
                pass
            elif name == b'rdma':
                pass
            elif name == b'memory':
                pass
            elif name == b'pids':
                pass
            elif name == b'devices':
                pass
            elif name == b'hugetlb':
                pass
            elif name == b'net_prio':
                pass
            elif name == b'net_cls':
                pass
            elif name == b'net_cls,net_prio':
                pass
            elif name == b'blkio':
                pass
            elif name == b'freezer':
                pass
            elif name == b'cpuacct':
                pass
            elif name == b'cpu':
                pass
            elif name == b'cpu,cpuacct':
                pass
            elif name == b'perf_event':
                pass
            elif name == b'systemd':
                pass
            elif name == b'unified':
                pass
            else:
                raise NotImplementedError("Unknown name in cgroup tree!")

        # Optionally we can remount the filesystem if we need access to it
        # ret = os.system("mount / --rbind %s -o nosuid,nodev,ro" % NetWorkSettings.CHROOT_DIR)
        # if ret != 0:
        #     raise RuntimeError("Error executing mount command: %s" % ret)
        #
        # # chroot to empty
        # os.chroot(NetWorkSettings.CHROOT_DIR)
        # os.chdir("/")

        # chroot to empty directory, provide the process with no filesystem access
        os.chroot(NetWorkSettings.CHROOT_DIR)

        # drop capabilities
        print("Dropped capabilities: ", end=" ", file=sys.stderr)
        for capname in dir(prctl.cap_effective):
            value = getattr(prctl.cap_effective, capname)
            if capname.startswith("__") or type(value) is not bool:
                continue

            setattr(prctl.cap_effective, capname, False)
            print(capname, end=", ", file=sys.stderr)
        print(file=sys.stderr)

        capabilities = []
        for capname in dir(prctl.cap_effective):
            value = getattr(prctl.cap_effective, capname)
            if value is True:
                capabilities.append(capname)

        if len(capabilities) > 0:
            raise RuntimeError("Unable to drop capabilities: %s" % capabilities)
        # end

        # limit system calls accessible with seccomp to reduce kernel attack surface,
        # an image converter probably only needs to read and write files, possibly mmap
        # TODO

        # monitoring: report failed invocation of the image converter and detect anomalies
        # we need to prevent attackers from hammering this interface with requests, as the defenses are probabilistic
        # TODO

        # set no new privs
        prctl.set_no_new_privs(1)
        print("Set no new privs: %s" % prctl.get_no_new_privs(), file=sys.stderr)

        # set proctitle
        newtitle = "### Restricted Image Converter ###"
        prctl.set_proctitle(newtitle)
        print("Setting new proctitle to: %s" % newtitle, file=sys.stderr)

        # execute payload
        print("Top level directories:", file=sys.stderr)
        print(os.listdir("/"), file=sys.stderr)

        # print privileges
        print("UID: %s, EUID: %s, GID: %s, EGID: %s, GROUPS: %s" % (
            os.getuid(), os.geteuid(), os.getgid(), os.getegid(), os.getgroups()), file=sys.stderr)

        # activating seccomp
        # TODO: this currently terminates the process, since it needs more than read() and write()
        # print("Old Seccomp: %s" % prctl.get_seccomp(), file=sys.stderr)
        # prctl.set_seccomp(1)
        # print("New Seccomp: %s" % prctl.get_seccomp(), file=sys.stderr)

    def parse(self):
        # this function parses the image coming in from stdin and outputs the converted image to stdout

        original_image = sys.stdin.buffer.read()
        input_buffer = io.BytesIO(initial_bytes=original_image)
        tmp = Image.open(input_buffer)

        conversion_buffer = io.BytesIO()
        tmp.save(conversion_buffer, format="png")
        sys.stdout.buffer.write(conversion_buffer.getvalue())


if __name__ == "__main__":
    x = ImageParse()
    x.parse()
    print("DONE", file=sys.stderr)
