"""CNAB 240 return files (arquivo de retorno de cobranca), FEBRABAN layout.

Positions follow the FEBRABAN 240 standard used by most Brazilian banks. Each paid or
changed title comes as a pair of detail records: segment T (title data) followed by
segment U (amounts and dates).
"""

from __future__ import annotations

from ._fixed import Field, Record, parse_record, split_lines
from .errors import IntegrityError, LayoutError
from .models import Movement, ReturnFile

WIDTH = 240

FILE_HEADER = {
    "bank_code": Field(1, 3),
    "record_type": Field(8, 8),
    "company_doc_type": Field(18, 18),
    "company_document": Field(19, 32),
    "company_name": Field(73, 102),
    "bank_name": Field(103, 132),
    "direction": Field(143, 143),  # 1 = remessa (to the bank), 2 = retorno (from the bank)
    "generated_on": Field(144, 151, "date8"),
    "sequence": Field(158, 163, "int"),
    "layout_version": Field(164, 166),
}

SEGMENT_T = {
    "lot": Field(4, 7, "int"),
    "segment": Field(14, 14),
    "occurrence_code": Field(16, 17),
    "our_number": Field(38, 57),
    "wallet": Field(58, 58),
    "document_number": Field(59, 73),
    "due_date": Field(74, 81, "date8"),
    "amount": Field(82, 96, "money"),
    "payer_doc_type": Field(133, 133),
    "payer_document": Field(134, 148),
    "payer_name": Field(149, 188),
    "fee": Field(199, 213, "money"),
    "reasons": Field(214, 223),
}

SEGMENT_U = {
    "lot": Field(4, 7, "int"),
    "segment": Field(14, 14),
    "occurrence_code": Field(16, 17),
    "interest": Field(18, 32, "money"),
    "discount": Field(33, 47, "money"),
    "rebate": Field(48, 62, "money"),
    "iof": Field(63, 77, "money"),
    "paid_amount": Field(78, 92, "money"),
    "credited_amount": Field(93, 107, "money"),
    "other_expenses": Field(108, 122, "money"),
    "other_credits": Field(123, 137, "money"),
    "occurrence_date": Field(138, 145, "date8"),
    "credit_date": Field(146, 153, "date8"),
}

LOT_TRAILER = {"lot": Field(4, 7, "int"), "records": Field(18, 23, "int")}
FILE_TRAILER = {"lots": Field(18, 23, "int"), "records": Field(24, 29, "int")}

# Codigos de movimento retorno (FEBRABAN, nota C044) most systems need to act on.
OCCURRENCES = {
    "02": "Entrada confirmada",
    "03": "Entrada rejeitada",
    "06": "Liquidacao",
    "09": "Baixa",
    "12": "Confirmacao de abatimento",
    "14": "Confirmacao de alteracao de vencimento",
    "17": "Liquidacao apos baixa",
    "28": "Debito de tarifas/custas",
}


def parse(data: str | bytes) -> ReturnFile:
    """Parse a CNAB 240 return file. Raises LayoutError or IntegrityError on bad input."""
    lines = split_lines(data, WIDTH)
    if not lines:
        raise LayoutError("empty file")

    header = parse_record(lines[0], FILE_HEADER, 1)
    if header.text("record_type") != "0":
        raise LayoutError("line 1: the file must start with a file header (record type 0)")
    if header.text("direction") != "2":
        raise LayoutError("this is not a return file (header position 143 must be '2')")

    movements: list[Movement] = []
    lots = 0
    lot_records = 0
    pending_t: tuple[int, Record] | None = None

    for no, line in enumerate(lines, start=1):
        kind = line[7]
        if pending_t is not None and not (kind == "3" and line[13] == "U"):
            raise LayoutError(f"line {pending_t[0]}: segment T without its segment U")
        if kind == "1":
            lots += 1
            lot_records = 1
            continue
        lot_records += 1 if kind in "35" else 0
        if kind == "3":
            segment = line[13]
            if segment == "T":
                pending_t = (no, parse_record(line, SEGMENT_T, no))
            elif segment == "U":
                if pending_t is None:
                    raise LayoutError(f"line {no}: segment U without a preceding segment T")
                movements.append(_movement(pending_t[1], parse_record(line, SEGMENT_U, no), pending_t[0]))
                pending_t = None
            # Other segments (Y, W...) are optional extras and are skipped.
        elif kind == "5":
            trailer = parse_record(line, LOT_TRAILER, no)
            if trailer.number("records") != lot_records:
                raise IntegrityError(
                    f"line {no}: lot trailer says {trailer.number('records')} records, found {lot_records}"
                )
        elif kind == "9":
            trailer = parse_record(line, FILE_TRAILER, no)
            if trailer.number("records") != len(lines):
                raise IntegrityError(
                    f"file trailer says {trailer.number('records')} records, found {len(lines)}"
                )
            if trailer.number("lots") != lots:
                raise IntegrityError(f"file trailer says {trailer.number('lots')} lots, found {lots}")

    if pending_t is not None:
        raise LayoutError(f"line {pending_t[0]}: segment T without its segment U")
    if lines[-1][7] != "9":
        raise IntegrityError("the file does not end with a file trailer (record type 9)")

    return ReturnFile(
        layout="cnab240",
        bank_code=header.text("bank_code"),
        bank_name=header.text("bank_name"),
        company_name=header.text("company_name"),
        company_document=header.text("company_document"),
        generated_on=header.day("generated_on"),
        sequence=header.number("sequence"),
        movements=movements,
    )


def _movement(t: Record, u: Record, line: int) -> Movement:
    code = t.text("occurrence_code")
    return Movement(
        our_number=t.text("our_number"),
        document_number=t.text("document_number"),
        occurrence_code=code,
        occurrence=OCCURRENCES.get(code, ""),
        occurrence_date=u.day("occurrence_date"),
        due_date=t.day("due_date"),
        amount=t.money("amount"),
        paid_amount=u.money("paid_amount"),
        credited_amount=u.money("credited_amount"),
        fee=t.money("fee"),
        interest=u.money("interest"),
        discount=u.money("discount"),
        rebate=u.money("rebate"),
        credit_date=u.day("credit_date"),
        payer_name=t.text("payer_name"),
        payer_document=t.text("payer_document").lstrip("0"),
        line=line,
    )
