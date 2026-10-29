from datetime import date
from decimal import Decimal

import pytest

from cnabkit import LayoutError, ofx

SGML = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS><DTSERVER>20240131120000[-3:BRT]<LANGUAGE>POR</SONRS></SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1
<STMTRS>
<CURDEF>BRL
<BANKACCTFROM>
<BANKID>0341
<BRANCHID>1234
<ACCTID>56789-0
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101000000[-3:BRT]
<DTEND>20240131000000[-3:BRT]
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20240115000000[-3:BRT]
<TRNAMT>1.250,75
<FITID>202401150001
<MEMO>PIX RECEBIDO JOSÉ
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20240120
<TRNAMT>-89.90
<FITID>202401200002
<CHECKNUM>000123
<NAME>CONTA DE LUZ
</STMTTRN>
</BANKTRANLIST>
<LEDGERBAL>
<BALAMT>3160.85
<DTASOF>20240131
</LEDGERBAL>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

XML = """<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="220" SECURITY="NONE"?>
<OFX>
  <BANKMSGSRSV1><STMTTRNRS><STMTRS>
    <CURDEF>BRL</CURDEF>
    <BANKACCTFROM><BANKID>0001</BANKID><ACCTID>998877</ACCTID></BANKACCTFROM>
    <BANKTRANLIST>
      <DTSTART>20240201</DTSTART><DTEND>20240229</DTEND>
      <STMTTRN><TRNTYPE>XFER</TRNTYPE><DTPOSTED>20240210</DTPOSTED><TRNAMT>-500.00</TRNAMT>
        <FITID>X1</FITID><MEMO>TED ENVIADA</MEMO></STMTTRN>
    </BANKTRANLIST>
  </STMTRS></STMTTRNRS></BANKMSGSRSV1>
</OFX>
"""

CREDIT_CARD = """<OFX><CREDITCARDMSGSRSV1><CCSTMTTRNRS><CCSTMTRS><CURDEF>BRL
<CCACCTFROM><ACCTID>4111XXXXXXXX1111</CCACCTFROM>
<BANKTRANLIST><STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20240305<TRNAMT>-42.00<FITID>C1<MEMO>MERCADO</STMTTRN></BANKTRANLIST>
</CCSTMTRS></CCSTMTTRNRS></CREDITCARDMSGSRSV1></OFX>
"""


def test_reads_ofx_1_sgml_in_cp1252():
    (st,) = ofx.parse(SGML.encode("cp1252"))
    assert (st.bank_id, st.branch_id, st.account_id, st.currency) == ("0341", "1234", "56789-0", "BRL")
    assert st.start == date(2024, 1, 1)
    assert st.end == date(2024, 1, 31)
    assert st.balance == Decimal("3160.85")
    assert st.balance_date == date(2024, 1, 31)

    credit, debit = st.transactions
    assert credit.amount == Decimal("1250.75")
    assert credit.memo == "PIX RECEBIDO JOSÉ"
    assert credit.posted == date(2024, 1, 15)
    assert debit.amount == Decimal("-89.90")
    assert debit.check_number == "000123"
    assert debit.name == "CONTA DE LUZ"
    assert st.total == Decimal("1160.85")


def test_reads_ofx_2_xml():
    (st,) = ofx.parse(XML)
    assert st.bank_id == "0001"
    (t,) = st.transactions
    assert (t.type, t.fitid, t.amount, t.memo) == ("XFER", "X1", Decimal("-500.00"), "TED ENVIADA")


def test_reads_credit_card_statements():
    (st,) = ofx.parse(CREDIT_CARD)
    assert st.account_id == "4111XXXXXXXX1111"
    assert st.transactions[0].amount == Decimal("-42.00")


def test_rejects_files_without_ofx():
    with pytest.raises(LayoutError, match="no <OFX>"):
        ofx.parse("not an ofx file")


def test_rejects_bad_amounts():
    with pytest.raises(LayoutError, match="invalid amount"):
        ofx.parse(XML.replace("-500.00", "abc"))
