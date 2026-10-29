from datetime import date
from decimal import Decimal

import pytest

from cnabkit import IntegrityError, LayoutError, cnab240, parse_return
from tests.builders import cnab240_file


def test_parses_settlement_and_registration():
    result = cnab240.parse(cnab240_file())
    assert result.layout == "cnab240"
    assert result.bank_code == "001"
    assert result.company_document == "12345678000199"
    assert result.generated_on == date(2024, 1, 15)
    assert result.sequence == 42
    assert len(result.movements) == 2

    paid, new = result.movements
    assert paid.is_settlement
    assert paid.occurrence == "Liquidacao"
    assert paid.our_number == "00000000000000012345"
    assert paid.document_number == "NF-1001"
    assert paid.amount == Decimal("100.00")
    assert paid.paid_amount == Decimal("101.50")
    assert paid.interest == Decimal("1.50")
    assert paid.credited_amount == Decimal("99.50")
    assert paid.fee == Decimal("2.00")
    assert paid.due_date == date(2024, 1, 10)
    assert paid.occurrence_date == date(2024, 1, 12)
    assert paid.credit_date == date(2024, 1, 13)
    assert paid.payer_name == "MARIA DA SILVA"
    assert paid.payer_document == "12345678909"
    assert paid.line == 3

    assert not new.is_settlement
    assert new.occurrence == "Entrada confirmada"
    assert new.credit_date is None
    assert result.settlements == [paid]
    assert result.total_paid == Decimal("101.50")


def test_accepts_bytes_and_detects_layout():
    assert parse_return(cnab240_file().encode("latin-1")).layout == "cnab240"


def test_rejects_wrong_record_count():
    with pytest.raises(IntegrityError, match="found 8"):
        cnab240.parse(cnab240_file(records=99))


def test_rejects_remittance_files():
    with pytest.raises(LayoutError, match="not a return file"):
        cnab240.parse(cnab240_file(direction="1"))


def test_rejects_segment_t_without_u():
    with pytest.raises(LayoutError, match="segment T without its segment U"):
        cnab240.parse(cnab240_file(drop_u=True))


def test_reports_line_with_wrong_width():
    lines = cnab240_file().split("\r\n")
    lines[2] = lines[2][:-1]
    with pytest.raises(LayoutError, match="line 3: expected 240"):
        cnab240.parse("\r\n".join(lines))
