import datetime
import unittest

from custom_components.tge.connector import TgeConnector


class _FakeCell:
    def __init__(self, text: str) -> None:
        self.text = text

    def get_text(self, strip: bool = False) -> str:
        return self.text.strip() if strip else self.text


class _FakeRow:
    def __init__(self, cells: list[str]) -> None:
        self._cells = [_FakeCell(c) for c in cells]

    def select(self, selector: str):
        if selector != "td":
            return []
        return self._cells


class TestTgeConnectorParsing(unittest.TestCase):
    def test_optional_float_parsing(self) -> None:
        self.assertIsNone(TgeConnector._parse_optional_float("-"))
        self.assertIsNone(TgeConnector._parse_optional_float("—"))
        self.assertEqual(TgeConnector._parse_optional_float("1 234,56"), 1234.56)
        self.assertEqual(TgeConnector._parse_optional_float("1.234,56"), 1234.56)
        self.assertEqual(TgeConnector._parse_optional_float("312,50"), 312.50)

    def test_parse_row_fixing2_missing_is_none(self) -> None:
        delivery_date = datetime.date(2026, 5, 7)
        row = _FakeRow(
            [
                f"{delivery_date.isoformat()}_H01",  # instrument
                "60",
                "100,00",
                "1 000,00",
                "-",  # fixing2_rate missing
                "-",  # fixing2_volume missing
            ]
        )
        parsed = TgeConnector._parse_row(row, delivery_date)
        self.assertEqual(parsed.fixing1_rate, 100.0)
        self.assertEqual(parsed.fixing1_volume, 1000.0)
        self.assertIsNone(parsed.fixing2_rate)
        self.assertIsNone(parsed.fixing2_volume)

    def test_dst_spring_forward_23_hours(self) -> None:
        # Poland DST spring-forward in 2026: 2026-03-29 has 23 hours (02:00 missing)
        delivery_date = datetime.date(2026, 3, 29)
        # Ordinal 0 -> 00:00
        self.assertEqual(TgeConnector._ordinal_hour_to_local_dt(delivery_date, 0).hour, 0)
        # Ordinal 2 should map to 03:00 local time on spring-forward day.
        self.assertEqual(TgeConnector._ordinal_hour_to_local_dt(delivery_date, 2).hour, 3)

    def test_dst_fall_back_25_hours(self) -> None:
        # Poland DST fall-back in 2026: 2026-10-25 has 25 hours (02:00 repeats)
        delivery_date = datetime.date(2026, 10, 25)
        # The repeated 02:00 hour should appear twice with different UTC offsets.
        # ordinal 2 (H03) -> 02:00+02:00 (before switch)
        # ordinal 3 (H04) -> 02:00+01:00 (after switch)
        dt2 = TgeConnector._ordinal_hour_to_local_dt(delivery_date, 2)
        dt3 = TgeConnector._ordinal_hour_to_local_dt(delivery_date, 3)
        self.assertEqual(dt2.hour, 2)
        self.assertEqual(dt3.hour, 2)
        self.assertNotEqual(dt2.utcoffset(), dt3.utcoffset())


if __name__ == "__main__":
    unittest.main()

