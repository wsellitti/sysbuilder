"""Exceptions for sysbuilder."""


class _SysBuilderException(Exception):
    """Generic sysbuilder exception."""


class BlockDeviceExistsException(_SysBuilderException):
    """Unexpected block device file found."""


class BlockDeviceNotFoundException(_SysBuilderException):
    """Expected block device missing."""


class DeviceActivationException(_SysBuilderException):
    """Cannot activate device."""


class PartitionCreateError(_SysBuilderException):
    """Unable to partition a device."""


class ProbeError(_SysBuilderException):
    """Device Probe failed."""
