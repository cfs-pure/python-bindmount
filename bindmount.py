import ctypes
import ctypes.util
import os

class BindMount(object):
    """ Context manager that folds the filesystem namespace using bind
        mounts.
        
        source (str):
            Path of directory that will be attached to the target directory
        target (str):
            Path of directory which will be attached to the source directory
    """

    def __init__(self, source, target):
        self._source = source
        self._target = target

    @cached_property
    def _libc(self):
        """ Convenience property that initializes access to libc.so
        """
        return ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)

    @cached_property
    def _libc_mount(self):
        """ Convenience property that initializes and returns the mount(2)
            function as a Python method.
        """
        self._libc.mount.argtypes = (ctypes.c_char_p,
                                     ctypes.c_char_p,
                                     ctypes.c_char_p,
                                     ctypes.c_ulong,
                                     ctypes.c_void_p)
        return self._libc.mount

    @cached_property
    def _libc_umount(self):
        """ Convenience property that initializes and returns the umount(2)
            function as a Python method.
        """
        self._libc.umount.argtypes = (ctypes.c_char_p, ) # tuple
        return self._libc.umount

    def mount(self, source, target, fstype, flags, data):
        """ Wrapper that translates errors from mount(2) as OSError
        """
        if self._libc_mount(source, target, fstype, flags, data) < 0:
            errno = ctypes.get_errno()
            emsg = 'Could not bind mount {} to {}: {}'
            raise OSError(errno, emsg.format(source, target, os.strerror(errno)))

    def umount(self, target):
        """ Wrapper that translates errors from umount(2) as OSError
        """
        if self._libc_umount(target) < 0:
            errno = ctypes.get_errno()
            emsg = 'Could not unmount {}: {}'
            raise OSError(errno, emsg.format(target, os.strerror(errno)))

    def __enter__(self):
        """ Perform the bind mount for suite
        """
        # From /usr/include/x86_64-linux-gnu/sys/mount.h:
        #   MS_BIND = 4096, /* Bind directory at different place.  */
        # NOTE: in Python ctypes, NoneType is the NULL pointer.
        self.mount(self._source, self._target, "", 4096, None)

    def __exit__(self, exc_type, exc_value, traceback):
        """ Unbind the mount now that the suite has been completed
        """
        self._libc_umount(self._target)
