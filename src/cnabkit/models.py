"""Bank-agnostic results returned by every parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Movement:
    """One title (boleto) event from a CNAB return file (arquivo de retorno)."""

    our_number: str  # nosso numero: the bank's id for the title
    document_number: str  # seu numero / numero do documento: your id
    occurrence_code: str  # codigo de ocorrencia / movimento
    occurrence: str  # human description of the code, when known
    occurrence_date: date | None
    due_date: date | None
    amount: Decimal  # face value of the title
    paid_amount: Decimal
    credited_amount: Decimal | None  # net credited (CNAB 240 only)
    fee: Decimal  # bank fee (tarifa)
    interest: Decimal  # juros / multa
    discount: Decimal
    rebate: Decimal  # abatimento
    credit_date: date | None
    payer_name: str = ""
    payer_document: str = ""
    line: int = 0  # first line of the record in the file

    @property
    def is_settlement(self) -> bool:
        """True when the title was paid (liquidacao)."""
        return self.occurrence_code in {"06", "15", "17"}


@dataclass(frozen=True)
class ReturnFile:
    """A parsed CNAB return file."""

    layout: str  # "cnab240" | "cnab400"
    bank_code: str
    bank_name: str
    company_name: str
    company_document: str
    generated_on: date | None
    sequence: int  # NSA / numero sequencial do arquivo
    movements: list[Movement] = field(default_factory=list)

    @property
    def settlements(self) -> list[Movement]:
        return [m for m in self.movements if m.is_settlement]

    @property
    def total_paid(self) -> Decimal:
        return sum((m.paid_amount for m in self.settlements), Decimal("0"))
