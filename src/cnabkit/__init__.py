"""Parsers for Brazilian bank files: CNAB 240, CNAB 400 and OFX."""

from . import cnab240, cnab400, ofx
from .errors import CnabkitError, IntegrityError, LayoutError, UnsupportedBankError
from .models import Movement, ReturnFile


def parse_return(data: str | bytes) -> ReturnFile:
    """Parse a CNAB return file, picking CNAB 240 or 400 from the record width."""
    text = data.decode("latin-1") if isinstance(data, bytes) else data
    first = text.split("\n", 1)[0].rstrip("\r")
    if len(first) == cnab240.WIDTH:
        return cnab240.parse(text)
    if len(first) == cnab400.WIDTH:
        return cnab400.parse(text)
    raise LayoutError(f"unknown CNAB layout: first record has {len(first)} characters")


__all__ = [
    "CnabkitError",
    "IntegrityError",
    "LayoutError",
    "Movement",
    "ReturnFile",
    "UnsupportedBankError",
    "cnab240",
    "cnab400",
    "ofx",
    "parse_return",
]
__version__ = "0.1.0"
