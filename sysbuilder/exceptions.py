"""Exceptions for sysbuilder."""


class _SysBuilderError(Exception):
    """Generic sysbuilder exception."""


class BlockDeviceExistsError(_SysBuilderError):
    """A loop device exists when it should not."""


class BlockDeviceError(_SysBuilderError):
    """Generic error for block devices."""


class BlockDeviceNotFoundError(_SysBuilderError):
    """Cannot find loop a(ny) block device(s)."""


class LoopDeviceExistsError(_SysBuilderError):
    """A loop device exists when it should not."""


class LoopDeviceError(_SysBuilderError):
    """Generic error for loop devices."""


class LoopDeviceNotFoundError(_SysBuilderError):
    """Cannot find loop a(ny) loop device(s)."""


class FileSystemExistsError(_SysBuilderError):
    """A file system exists when it should not."""


class FileSystemError(_SysBuilderError):
    """Generic error for file systems."""


class FileSystemNotFoundError(_SysBuilderError):
    """Cannot find loop a(ny) file system(s)."""
