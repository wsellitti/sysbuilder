"""Exceptions for sysbuilder."""


class _SysBuilderError(Exception):
    """Generic sysbuilder exception."""


class BlockDeviceExistsError(_SysBuilderError):
    """Unexpected block device file found."""


class BlockDeviceNotFoundError(_SysBuilderError):
    """Expected block device missing."""


class DeviceActivationError(_SysBuilderError):
    """Cannot activate device."""


class PartitionCreateError(_SysBuilderError):
    """Unable to partition a device."""


class ProbeError(_SysBuilderError):
    """Device Probe failed."""
