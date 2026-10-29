"""Build synthetic fixed-width records from {start_position: value} maps (1-based, like the manuals)."""

from __future__ import annotations


def record(width: int, fields: dict[int, str]) -> str:
    buf = [" "] * width
    for start, value in fields.items():
        for i, ch in enumerate(value):
            buf[start - 1 + i] = ch
    return "".join(buf)


def num(value: int, size: int) -> str:
    return str(value).zfill(size)


def cnab240_file(*, records: int | None = None, direction: str = "2", drop_u: bool = False) -> str:
    header = record(
        240,
        {
            1: "001",
            4: "0000",
            8: "0",
            18: "2",
            19: "12345678000199",
            73: "EMPRESA EXEMPLO LTDA",
            103: "BANCO EXEMPLO",
            143: direction,
            144: "15012024",
            158: num(42, 6),
            164: "087",
        },
    )
    lot = record(240, {1: "001", 4: "0001", 8: "1", 9: "T", 10: "01", 14: "045"})
    paid_t = record(
        240,
        {
            1: "001",
            4: "0001",
            8: "3",
            9: num(1, 5),
            14: "T",
            16: "06",
            38: "00000000000000012345",
            58: "1",
            59: "NF-1001",
            74: "10012024",
            82: num(10000, 15),
            133: "1",
            134: num(12345678909, 15),
            149: "MARIA DA SILVA",
            199: num(200, 15),
        },
    )
    paid_u = record(
        240,
        {
            1: "001",
            4: "0001",
            8: "3",
            9: num(2, 5),
            14: "U",
            16: "06",
            18: num(150, 15),
            33: num(0, 15),
            48: num(0, 15),
            63: num(0, 15),
            78: num(10150, 15),
            93: num(9950, 15),
            108: num(0, 15),
            123: num(0, 15),
            138: "12012024",
            146: "13012024",
        },
    )
    new_t = record(
        240,
        {
            1: "001",
            4: "0001",
            8: "3",
            9: num(3, 5),
            14: "T",
            16: "02",
            38: "00000000000000012346",
            59: "NF-1002",
            74: "20022024",
            82: num(25990, 15),
            199: num(0, 15),
        },
    )
    new_u = record(
        240,
        {
            1: "001",
            4: "0001",
            8: "3",
            9: num(4, 5),
            14: "U",
            16: "02",
            18: num(0, 15),
            33: num(0, 15),
            48: num(0, 15),
            63: num(0, 15),
            78: num(0, 15),
            93: num(0, 15),
            108: num(0, 15),
            123: num(0, 15),
            138: "15012024",
            146: "00000000",
        },
    )
    lot_trailer = record(240, {1: "001", 4: "0001", 8: "5", 18: num(6, 6)})
    body = [header, lot, paid_t, paid_u, new_t] + ([] if drop_u else [new_u]) + [lot_trailer]
    total = records if records is not None else len(body) + 1
    trailer = record(240, {1: "001", 4: "9999", 8: "9", 18: num(1, 6), 24: num(total, 6)})
    return "\r\n".join([*body, trailer]) + "\r\n"


def bradesco400_file(*, bank: str = "237", break_sequence: bool = False) -> str:
    header = record(
        400,
        {
            1: "0",
            2: "2",
            3: "RETORNO",
            10: "01",
            12: "COBRANCA",
            27: num(4567, 20),
            47: "EMPRESA EXEMPLO LTDA",
            77: bank,
            80: "BRADESCO",
            95: "150124",
            109: num(7, 5),
            395: num(1, 6),
        },
    )
    paid = record(
        400,
        {
            1: "1",
            2: "02",
            4: "12345678000199",
            38: "PEDIDO-77",
            71: "000000123459",
            108: "9",
            109: "06",
            111: "120124",
            117: "NF-2001",
            147: "100124",
            153: num(10000, 13),
            176: num(250, 13),
            189: num(0, 13),
            202: num(0, 13),
            215: num(0, 13),
            228: num(0, 13),
            241: num(500, 13),
            254: num(9500, 13),
            267: num(0, 13),
            280: num(0, 13),
            296: "130124",
            395: num(2, 6),
        },
    )
    rejected = record(
        400,
        {
            1: "1",
            2: "02",
            4: "12345678000199",
            38: "PEDIDO-78",
            71: "000000123460",
            108: "9",
            109: "03",
            111: "150124",
            147: "200224",
            153: num(4990, 13),
            176: num(0, 13),
            189: num(0, 13),
            202: num(0, 13),
            215: num(0, 13),
            228: num(0, 13),
            241: num(0, 13),
            254: num(0, 13),
            267: num(0, 13),
            280: num(0, 13),
            296: "000000",
            319: "0000000017",
            395: num(4 if break_sequence else 3, 6),
        },
    )
    trailer = record(400, {1: "9", 2: "2", 3: "01", 5: "237", 395: num(4, 6)})
    return "\n".join([header, paid, rejected, trailer]) + "\n"
