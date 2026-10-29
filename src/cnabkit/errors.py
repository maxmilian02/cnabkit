class CnabkitError(Exception):
    """Base class for every error raised by cnabkit."""


class LayoutError(CnabkitError):
    """A record does not match the expected layout (wrong width, type or value)."""


class IntegrityError(CnabkitError):
    """The file is well-formed but inconsistent, e.g. trailer counts that do not match."""


class UnsupportedBankError(CnabkitError):
    """No layout is registered for this bank and file type."""
