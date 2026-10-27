"""
setupkit.exceptions - Exception hierarchy for setupkit.

All setupkit exceptions inherit from SetupKitError so callers
can catch the base class if they don't need to distinguish between
specific failure modes.

Exception hierarchy:
    SetupKitError
    ├── PluginConfigError     — plugin.yaml missing, unreadable, or invalid
    ├── ManifestError         — manifest.fletch fetch or parse failure
    ├── VersionError          — version string missing or unparseable
    └── InstallError          — pip install subprocess failure
"""


class SetupKitError(Exception):
    """Base exception for all setupkit errors."""


class PluginConfigError(SetupKitError):
    """
    Raised when a plugin.yaml file is missing, unreadable, or fails validation.

    Args:
        message: Human-readable description of the failure.
    """


class ManifestError(SetupKitError):
    """
    Raised when a manifest.fletch file cannot be fetched or parsed.

    Args:
        message: Human-readable description of the failure.
    """


class VersionError(SetupKitError):
    """
    Raised when a version string is missing, malformed, or cannot be compared.

    Args:
        message: Human-readable description of the failure.
    """


class InstallError(SetupKitError):
    """
    Raised when a pip install subprocess exits with a non-zero return code.

    Args:
        message: Human-readable description of the failure.
    """
