"""Exceptions for sysbuilder."""


class _SysBuilderException(Exception):
    """Generic sysbuilder exception."""


class DeviceExistsException(_SysBuilderException):
    """Unexpected device file found."""


class BlockDeviceExistsException(DeviceExistsException):
    """Unexpected block device file found."""


class DeviceNotFoundException(_SysBuilderException):
    """Expected device file missing."""


class BlockDeviceNotFoundException(DeviceNotFoundException):
    """Expected block device missing."""


class PartitionCreateError(_SysBuilderException):
    """Unable to partition a device."""


class ProbeError(_SysBuilderException):
    """Device Probe failed."""
