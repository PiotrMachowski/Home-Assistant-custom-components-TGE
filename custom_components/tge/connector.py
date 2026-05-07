"""Connector for TGE integration."""

from __future__ import annotations

import datetime
import logging
import re
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from .const import DATA_URL_TEMPLATE

_LOGGER = logging.getLogger(__name__)

WARSAW_TZ = ZoneInfo("Europe/Warsaw")
UTC_TZ = ZoneInfo("UTC")

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


@dataclass
class TgeHourData:
    time: datetime.datetime
    fixing1_rate: float
    fixing1_volume: float
    fixing2_rate: float | None
    fixing2_volume: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "fixing1_rate": self.fixing1_rate,
            "fixing1_volume": self.fixing1_volume,
            "fixing2_rate": self.fixing2_rate,
            "fixing2_volume": self.fixing2_volume
        }

    @staticmethod
    def from_dict(value: dict[str, Any]) -> TgeHourData:
        time = datetime.datetime.fromisoformat(value.get("time"))
        fixing1_rate = value.get("fixing1_rate") or 0.0
        fixing1_volume = value.get("fixing1_volume") or 0.0
        fixing2_rate = value.get("fixing2_rate")
        fixing2_volume = value.get("fixing2_volume")
        return TgeHourData(time, fixing1_rate, fixing1_volume, fixing2_rate, fixing2_volume)


@dataclass
class TgeDayData:
    date: datetime.date
    hours: list[TgeHourData]

    @staticmethod
    def from_dict(value: dict[str, Any]) -> TgeDayData:
        date = datetime.datetime.fromisoformat(value.get("date")).date()
        hours = [TgeHourData.from_dict(h) for h in value.get("hours")]
        return TgeDayData(date, hours)

    def to_dict(self):
        return {
            "date": self.date.isoformat(),
            "hours": [h.to_dict() for h in self.hours]
        }


@dataclass
class TgeData:
    data: list[TgeDayData]


@dataclass
class TgeException(Exception):
    msg: str


class TgeConnector:

    @staticmethod
    def get_data() -> TgeData:
        data_for_today = TgeConnector.get_data_for_date(datetime.date.today())
        data_for_tomorrow = TgeConnector.get_data_for_date(datetime.date.today() + datetime.timedelta(days=1))
        data = [d for d in [data_for_today, data_for_tomorrow] if d is not None]
        return TgeData(data)

    @staticmethod
    def get_data_for_date(date: datetime.date) -> TgeDayData | None:
        _LOGGER.debug("Downloading TGE data for date {}...", date)
        response = requests.get(
            DATA_URL_TEMPLATE.format((date - datetime.timedelta(days=1)).strftime("%d-%m-%Y")),
            headers=_BROWSER_HEADERS,
            timeout=30,
        )
        _LOGGER.debug("Downloaded TGE data for date {} [{}]", date, response.status_code)
        if response.status_code != 200:
            _LOGGER.error("Failed to download TGE data: {}", response.status_code)
            raise TgeException("Failed to download TGE data")
        parser = BeautifulSoup(response.text, "html.parser")
        date_of_data = TgeConnector._get_date_of_data(parser)
        if date != date_of_data:
            return None
        data = TgeConnector._parse_timetable(parser, date)
        if len(list(filter(lambda d: d.fixing1_rate != 0, data))) == 0:
            return None
        return TgeDayData(date, data)

    @staticmethod
    def _get_date_of_data(html_parser: Any) -> datetime.date:
        # On the new page format, ".kontrakt-date" contains a <small> like
        # "dla dostawy w dniu DD-MM-YYYY" (but text around it may change).
        # We search any DD-MM-YYYY occurrences and take the last one.
        for el in html_parser.select(".kontrakt-date"):
            text = el.get_text(strip=True)
            found = re.findall(r"\d{2}-\d{2}-\d{4}", text)
            if not found:
                continue
            return datetime.datetime.strptime(found[-1], "%d-%m-%Y").date()

        _LOGGER.error("No date of data found")
        raise TgeException("No date of data found")

    @staticmethod
    def _parse_timetable(html_parser: Any, date_of_data: datetime.date) -> list[TgeHourData]:
        return [
            TgeConnector._parse_row(row, date_of_data)
            for row in TgeConnector._get_rows_of_table(html_parser)
        ]

    @staticmethod
    def _get_rows_of_table(html_parser: Any) -> list[Any]:
        tbody = html_parser.select_one("#rdn > tbody")
        if tbody is None:
            return []
        all_rows = tbody.select("tr")
        filtered_rows: list[Any] = []
        for row in all_rows:
            tds = row.select("td")
            if len(tds) < 6:
                continue
            instrument = tds[0].get_text(strip=True)
            if re.search(r"_H\d{2}$", instrument):
                filtered_rows.append(row)
        return filtered_rows

    @staticmethod
    def _parse_row(row: Any, date_of_data: datetime.date) -> TgeHourData:
        time_of_row = TgeConnector._get_time_of_row(row, date_of_data)
        # New table format (#rdn):
        # td[0] instrument e.g. "YYYY-MM-DD_H01"
        # td[1] instrument type "60" for hourly
        # Fixing I:  td[2]=Kurs [PLN/MWh], td[3]=Wolumen [MW]
        # Fixing II: td[4]=Kurs [PLN/MWh], td[5]=Wolumen [MW] (may be "-")
        fixing1_rate = TgeConnector._get_float_from_column(row, 2)
        fixing1_volume = TgeConnector._get_float_from_column(row, 3)
        fixing2_rate = TgeConnector._get_optional_float_from_column(row, 4)
        fixing2_volume = TgeConnector._get_optional_float_from_column(row, 5)
        return TgeHourData(time_of_row, fixing1_rate, fixing1_volume, fixing2_rate, fixing2_volume)

    @staticmethod
    def _get_time_of_row(row: Any, date_of_data: datetime.date) -> datetime.datetime:
        instrument = row.select("td")[0].get_text(strip=True)
        # "YYYY-MM-DD_H01" means the first hour of delivery day (00:00 local time).
        m = re.search(r"_H(\d{2})$", instrument)
        if not m:
            # Fallback to local midnight if format is unexpected.
            return datetime.datetime(
                date_of_data.year, date_of_data.month, date_of_data.day, 0, 0, 0, tzinfo=WARSAW_TZ
            )
        ordinal = int(m.group(1)) - 1
        return TgeConnector._ordinal_hour_to_local_dt(date_of_data, ordinal)

    @staticmethod
    def _ordinal_hour_to_local_dt(date_of_data: datetime.date, ordinal: int) -> datetime.datetime:
        """
        Convert an ordinal hour (0..23/24) to a timezone-aware local datetime.

        TGE uses hourly instruments H01, H02, ... in chronological order.
        On DST transition days, the delivery day can have 23 or 25 hours.

        Algorithm:
        - take local midnight in Warsaw timezone
        - convert to UTC
        - add ordinal hours in UTC
        - convert back to Warsaw timezone
        """
        local_midnight = datetime.datetime(
            date_of_data.year,
            date_of_data.month,
            date_of_data.day,
            0,
            0,
            0,
            tzinfo=WARSAW_TZ,
        )
        midnight_utc = local_midnight.astimezone(UTC_TZ)
        utc_dt = midnight_utc + datetime.timedelta(hours=ordinal)
        return utc_dt.astimezone(WARSAW_TZ)

    @staticmethod
    def _get_float_from_column(row: Tag, number: int) -> float:
        return TgeConnector._parse_float(TgeConnector._get_column_with_number(row, number), 0)

    @staticmethod
    def _get_optional_float_from_column(row: Tag, number: int) -> float | None:
        return TgeConnector._parse_optional_float(TgeConnector._get_column_with_number(row, number))

    @staticmethod
    def _get_column_with_number(row: Tag, number: int) -> str:
        return row.select("td")[number].text.strip()

    @staticmethod
    def _parse_float(value: str, default: float) -> float:
        parsed = TgeConnector._parse_optional_float(value)
        return default if parsed is None else parsed

    @staticmethod
    def _parse_optional_float(value: str) -> float | None:
        text = value.strip().replace("\xa0", " ").replace("\u202f", " ")
        if text in ("", "-", "—", "N/A", "n/a", "brak"):
            return None

        # Remove thousand separators
        text = text.replace(" ", "")

        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")

        try:
            return float(text)
        except ValueError:
            return None


if __name__ == '__main__':
    print(TgeConnector.get_data())
