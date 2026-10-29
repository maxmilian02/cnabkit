"""Fixed-width record helpers.

Bank manuals describe every field by 1-based, inclusive positions ("posicao 038 a 057").
Layouts here use the same numbers, so a field can be checked against the manual by eye.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .errors import LayoutError


@dataclass(frozen=True)
class Field:
    start: int  # 1-based, inclusive (as printed in the bank manual)
    end: int  # 1-based, inclusive
    kind: str = "str"  # str | int | money | date8 (DDMMAAAA) | date6 (DDMMAA)
    decimals: int = 2

    def raw(self, line: str) -> str:
        return line[self.start - 1 : self.end]


def parse_field(line: str, field: Field, name: str, line_no: int) -> object:
    raw = field.raw(line)
    try:
        if field.kind == "str":
            return raw.strip()
        if field.kind == "int":
            digits = raw.strip()
            return int(digits) if digits else 0
        if field.kind == "money":
            digits = raw.strip() or "0"
            if not digits.isdigit():
                raise ValueError(digits)
            return Decimal(digits).scaleb(-field.decimals)
        if field.kind in ("date8", "date6"):
            return _parse_date(raw, field.kind)
    except ValueError as exc:
        raise LayoutError(
            f"line {line_no}: field {name!r} (pos {field.start}-{field.end}) = {raw!r}"
        ) from exc
    raise LayoutError(f"unknown field kind {field.kind!r}")


def _parse_date(raw: str, kind: str) -> date | None:
    raw = raw.strip()
    if not raw or set(raw) == {"0"}:
        return None
    day, month = int(raw[0:2]), int(raw[2:4])
    if kind == "date8":
        year = int(raw[4:8])
    else:
        yy = int(raw[4:6])
        # CNAB 400 uses two-digit years; anything past 70 is last century.
        year = 1900 + yy if yy > 70 else 2000 + yy
    return date(year, month, day)


class Record(dict[str, object]):
    """Parsed record with typed accessors, so callers never need casts."""

    def text(self, name: str) -> str:
        v = self[name]
        assert isinstance(v, str)
        return v

    def number(self, name: str) -> int:
        v = self[name]
        assert isinstance(v, int)
        return v

    def money(self, name: str) -> Decimal:
        v = self[name]
        assert isinstance(v, Decimal)
        return v

    def day(self, name: str) -> date | None:
        v = self[name]
        assert v is None or isinstance(v, date)
        return v


def parse_record(line: str, layout: dict[str, Field], line_no: int) -> Record:
    return Record({name: parse_field(line, f, name, line_no) for name, f in layout.items()})


def split_lines(data: str | bytes, width: int) -> list[str]:
    """Split a CNAB file into records, checking that every record has the layout width."""
    text = data.decode("latin-1") if isinstance(data, bytes) else data
    lines = [ln.rstrip("\r") for ln in text.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    for no, ln in enumerate(lines, start=1):
        if len(ln) != width:
            raise LayoutError(f"line {no}: expected {width} characters, found {len(ln)}")
    return lines
