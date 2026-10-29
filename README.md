# cnabkit

Parsers for Brazilian bank files, with typed models and `Decimal` money:

- **CNAB 240** return files (arquivo de retorno de cobranca), FEBRABAN layout, segments T and U
- **CNAB 400** return files, layout registered per bank (Bradesco today)
- **OFX** statements, both 1.x (SGML, cp1252, decimal comma) and 2.x (XML), checking and credit card

No runtime dependencies. Python 3.10+.

## Why

Every Brazilian company that issues boletos or reconciles bank statements has to read these files.
The formats are fixed-width or almost-XML, vary by bank, and fail silently: a field read one column
off still "works" and books the wrong amount. cnabkit checks what the bank manuals let you check:
record width, trailer counts, sequence numbers and segment pairing, and it says which line and
field broke.

## Usage

```python
from pathlib import Path
import cnabkit
from cnabkit import ofx

ret = cnabkit.parse_return(Path("RETORNO.RET").read_bytes())  # picks CNAB 240 or 400
for m in ret.settlements:
    print(m.our_number, m.document_number, m.paid_amount, m.credit_date)
print("total paid:", ret.total_paid)

for statement in ofx.parse(Path("extrato.ofx").read_bytes()):
    for t in statement.transactions:
        print(t.posted, t.amount, t.memo, t.fitid)
```

Errors are explicit:

```text
LayoutError: line 3: expected 240 characters, found 239
IntegrityError: file trailer says 99 records, found 8
UnsupportedBankError: no CNAB 400 layout registered for bank 341
```

## Layouts

Fields are declared with the 1-based, inclusive positions printed in the bank manuals, so each
one can be checked against the manual by eye:

```python
"our_number": Field(38, 57),          # nosso numero
"amount": Field(82, 96, "money"),     # valor do titulo, 2 implied decimals
"due_date": Field(74, 81, "date8"),   # DDMMAAAA
```

Adding a CNAB 400 bank means describing its detail record in a `BankLayout` and registering it
under the bank code.

## Development

```bash
uv sync
uv run pytest
uv run ruff check . && uv run mypy
```

Test files are synthetic and built position by position in `tests/builders.py`; no real bank data
is stored in this repository.

## Roadmap

- More CNAB 400 banks (Itau, Banco do Brasil, Santander, Caixa)
- Remittance files (arquivo de remessa) for registering boletos
- Reconciliation service: FastAPI + PostgreSQL, matching CNAB settlements and OFX credits

## License

MIT
