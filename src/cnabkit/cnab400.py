"""CNAB 400 return files (arquivo de retorno de cobranca).

Unlike CNAB 240, the 400 layout is defined by each bank. Layouts are registered per
bank code; the bank is read from the file header (positions 077-079).

Registered: Bradesco (237), from the "Cobranca Bradesco - Layout 400 posicoes" manual.
To add a bank, describe its detail record in a new BankLayout and register it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._fixed import Field, Record, parse_record, split_lines
from .errors import IntegrityError, LayoutError, UnsupportedBankError
from .models import Movement, ReturnFile

WIDTH = 400

HEADER = {
    "record_type": Field(1, 1),
    "direction": Field(2, 2),  # 1 = remessa, 2 = retorno
    "service": Field(12, 26),
    "company_code": Field(27, 46),
    "company_name": Field(47, 76),
    "bank_code": Field(77, 79),
    "bank_name": Field(80, 94),
    "generated_on": Field(95, 100, "date6"),
    "notice_number": Field(109, 113, "int"),
}

SEQUENCE = Field(395, 400, "int")


@dataclass(frozen=True)
class BankLayout:
    name: str
    detail: dict[str, Field]
    occurrences: dict[str, str]


BRADESCO = BankLayout(
    name="Bradesco",
    detail={
        "company_doc_type": Field(2, 3),
        "company_document": Field(4, 17),
        "control_number": Field(38, 62),  # numero de controle do participante (uso da empresa)
        "our_number": Field(71, 82),
        "wallet": Field(108, 108),
        "occurrence_code": Field(109, 110),
        "occurrence_date": Field(111, 116, "date6"),
        "document_number": Field(117, 126),
        "due_date": Field(147, 152, "date6"),
        "amount": Field(153, 165, "money"),
        "fee": Field(176, 188, "money"),
        "other_expenses": Field(189, 201, "money"),
        "late_interest_op": Field(202, 214, "money"),
        "iof": Field(215, 227, "money"),
        "rebate": Field(228, 240, "money"),
        "discount": Field(241, 253, "money"),
        "paid_amount": Field(254, 266, "money"),
        "interest": Field(267, 279, "money"),
        "other_credits": Field(280, 292, "money"),
        "credit_date": Field(296, 301, "date6"),
        "reasons": Field(319, 328),
    },
    occurrences={
        "02": "Entrada confirmada",
        "03": "Entrada rejeitada",
        "06": "Liquidacao normal",
        "09": "Baixado automaticamente",
        "10": "Baixado conforme instrucoes",
        "12": "Abatimento concedido",
        "14": "Vencimento alterado",
        "15": "Liquidacao em cartorio",
        "17": "Liquidacao apos baixa",
        "28": "Debito de tarifas/custas",
    },
)

LAYOUTS: dict[str, BankLayout] = {"237": BRADESCO}


def parse(data: str | bytes) -> ReturnFile:
    """Parse a CNAB 400 return file for any registered bank."""
    lines = split_lines(data, WIDTH)
    if not lines:
        raise LayoutError("empty file")

    header = parse_record(lines[0], HEADER, 1)
    if header.text("record_type") != "0" or header.text("direction") != "2":
        raise LayoutError("line 1: expected a return-file header ('02RETORNO')")
    bank = header.text("bank_code")
    layout = LAYOUTS.get(bank)
    if layout is None:
        raise UnsupportedBankError(f"no CNAB 400 layout registered for bank {bank}")

    if lines[-1][0] != "9":
        raise IntegrityError("the file does not end with a trailer (record type 9)")
    for no, line in enumerate(lines, start=1):
        seq = parse_record(line, {"seq": SEQUENCE}, no).number("seq")
        if seq != no:
            raise IntegrityError(f"line {no}: sequence number is {seq}, expected {no}")

    movements = [
        _movement(parse_record(line, layout.detail, no), layout, no)
        for no, line in enumerate(lines, start=1)
        if line[0] == "1"
    ]
    return ReturnFile(
        layout="cnab400",
        bank_code=bank,
        bank_name=header.text("bank_name") or layout.name,
        company_name=header.text("company_name"),
        company_document=_company_doc(lines, layout),
        generated_on=header.day("generated_on"),
        sequence=header.number("notice_number"),
        movements=movements,
    )


def _company_doc(lines: list[str], layout: BankLayout) -> str:
    for no, line in enumerate(lines, start=1):
        if line[0] == "1":
            return parse_record(line, layout.detail, no).text("company_document").lstrip("0")
    return ""


def _movement(r: Record, layout: BankLayout, line: int) -> Movement:
    code = r.text("occurrence_code")
    return Movement(
        our_number=r.text("our_number"),
        document_number=r.text("document_number") or r.text("control_number"),
        occurrence_code=code,
        occurrence=layout.occurrences.get(code, ""),
        occurrence_date=r.day("occurrence_date"),
        due_date=r.day("due_date"),
        amount=r.money("amount"),
        paid_amount=r.money("paid_amount"),
        credited_amount=None,
        fee=r.money("fee"),
        interest=r.money("interest"),
        discount=r.money("discount"),
        rebate=r.money("rebate"),
        credit_date=r.day("credit_date"),
        line=line,
    )
