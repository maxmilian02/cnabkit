"""OFX bank statements, versions 1.x (SGML) and 2.x (XML).

Brazilian banks mostly export OFX 1.02: SGML where value tags are never closed,
cp1252 text, and dates such as 20240115120000[-3:BRT]. Some also write amounts
with a decimal comma. All of that is handled here without third-party packages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from .errors import LayoutError

_TAG = re.compile(r"<(/?)([A-Za-z0-9.]+)>([^<]*)")


@dataclass(frozen=True)
class Transaction:
    fitid: str  # the bank's unique id for the transaction; use it to deduplicate imports
    type: str  # CREDIT, DEBIT, PAYMENT, XFER...
    posted: date
    amount: Decimal  # negative for money leaving the account
    memo: str = ""
    name: str = ""
    check_number: str = ""


@dataclass(frozen=True)
class Statement:
    bank_id: str
    branch_id: str
    account_id: str
    currency: str
    start: date | None
    end: date | None
    balance: Decimal | None
    balance_date: date | None
    transactions: list[Transaction] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((t.amount for t in self.transactions), Decimal("0"))


@dataclass
class _Node:
    tag: str
    values: dict[str, str] = field(default_factory=dict)
    children: list[_Node] = field(default_factory=list)

    def find_all(self, tag: str) -> list[_Node]:
        found = [c for c in self.children if c.tag == tag]
        for c in self.children:
            found.extend(c.find_all(tag))
        return found

    def first(self, tag: str) -> _Node | None:
        hits = self.find_all(tag)
        return hits[0] if hits else None


def parse(data: str | bytes) -> list[Statement]:
    """Parse an OFX file and return one Statement per account in it."""
    text = _decode(data) if isinstance(data, bytes) else data
    start = text.upper().find("<OFX>")
    if start < 0:
        raise LayoutError("no <OFX> element found")
    root = _tree(text[start:])
    statements = root.find_all("STMTRS") + root.find_all("CCSTMTRS")
    if not statements:
        raise LayoutError("no statement (STMTRS or CCSTMTRS) in the file")
    return [_statement(s) for s in statements]


def _decode(raw: bytes) -> str:
    head = raw[:600].decode("ascii", errors="ignore").upper()
    if 'ENCODING="UTF-8"' in head or "ENCODING:UTF-8" in head or "CHARSET:UTF-8" in head:
        return raw.decode("utf-8")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _tree(body: str) -> _Node:
    root = _Node("ROOT")
    stack = [root]
    last_leaf: str | None = None
    for closing, tag, text in _TAG.findall(body):
        tag = tag.upper()
        value = text.strip()
        if closing:
            if tag == last_leaf:  # OFX 2.x closes value tags; nothing to do
                last_leaf = None
                continue
            # Close the aggregate, tolerating unclosed aggregates inside it.
            for i in range(len(stack) - 1, 0, -1):
                if stack[i].tag == tag:
                    del stack[i:]
                    break
            last_leaf = None
        elif value:
            stack[-1].values[tag] = value
            last_leaf = tag
        else:
            node = _Node(tag)
            stack[-1].children.append(node)
            stack.append(node)
            last_leaf = None
    return root


def _statement(node: _Node) -> Statement:
    acct = node.first("BANKACCTFROM") or node.first("CCACCTFROM") or _Node("EMPTY")
    tran_list = node.first("BANKTRANLIST") or _Node("EMPTY")
    bal = node.first("LEDGERBAL") or _Node("EMPTY")
    return Statement(
        bank_id=acct.values.get("BANKID", ""),
        branch_id=acct.values.get("BRANCHID", ""),
        account_id=acct.values.get("ACCTID", ""),
        currency=node.values.get("CURDEF", ""),
        start=_date(tran_list.values.get("DTSTART")),
        end=_date(tran_list.values.get("DTEND")),
        balance=_amount(bal.values["BALAMT"]) if "BALAMT" in bal.values else None,
        balance_date=_date(bal.values.get("DTASOF")),
        transactions=[_transaction(t) for t in tran_list.find_all("STMTTRN")],
    )


def _transaction(t: _Node) -> Transaction:
    v = t.values
    posted = _date(v.get("DTPOSTED"))
    if posted is None or "TRNAMT" not in v:
        raise LayoutError(f"transaction without DTPOSTED or TRNAMT: {v}")
    return Transaction(
        fitid=v.get("FITID", ""),
        type=v.get("TRNTYPE", ""),
        posted=posted,
        amount=_amount(v["TRNAMT"]),
        memo=v.get("MEMO", ""),
        name=v.get("NAME", ""),
        check_number=v.get("CHECKNUM", ""),
    )


def _date(raw: str | None) -> date | None:
    """Read YYYYMMDD[HHMMSS[.XXX]][[offset:TZ]]; only the calendar date matters here."""
    if not raw:
        return None
    digits = raw.strip()[:8]
    if len(digits) < 8 or not digits.isdigit():
        raise LayoutError(f"invalid OFX date {raw!r}")
    return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))


def _amount(raw: str) -> Decimal:
    s = raw.strip().replace(" ", "")
    if "," in s:  # decimal comma, possibly with dots as thousand separators
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise LayoutError(f"invalid amount {raw!r}") from exc
