from datetime import date
from decimal import Decimal

import pytest

from cnabkit import IntegrityError, UnsupportedBankError, cnab400, parse_return
from tests.builders import bradesco400_file


def test_parses_bradesco_return():
    result = cnab400.parse(bradesco400_file())
    assert result.layout == "cnab400"
    assert result.bank_code == "237"
    assert result.company_document == "12345678000199"
    assert result.generated_on == date(2024, 1, 15)
    assert result.sequence == 7

    paid, rejected = result.movements
    assert paid.is_settlement
    assert paid.occurrence == "Liquidacao normal"
    assert paid.our_number == "000000123459"
    assert paid.document_number == "NF-2001"
    assert paid.amount == Decimal("100.00")
    assert paid.discount == Decimal("5.00")
    assert paid.paid_amount == Decimal("95.00")
    assert paid.fee == Decimal("2.50")
    assert paid.credited_amount is None
    assert paid.credit_date == date(2024, 1, 13)

    assert rejected.occurrence == "Entrada rejeitada"
    assert rejected.document_number == "PEDIDO-78"
    assert rejected.due_date == date(2024, 2, 20)
    assert result.total_paid == Decimal("95.00")


def test_detects_layout_from_width():
    assert parse_return(bradesco400_file()).layout == "cnab400"


def test_unknown_bank_is_explicit():
    with pytest.raises(UnsupportedBankError, match="999"):
        cnab400.parse(bradesco400_file(bank="999"))


def test_checks_sequence_numbers():
    with pytest.raises(IntegrityError, match="line 3"):
        cnab400.parse(bradesco400_file(break_sequence=True))
