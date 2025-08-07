"""Connector for TGE integration."""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from .const import DATA_URL_TEMPLATE

_LOGGER = logging.getLogger(__name__)


@dataclass
class TgeHourData:
    time: datetime.datetime
    fixing1_rate: float
    fixing1_volume: float
    fixing2_rate: float
    fixing2_volume: float

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
        fixing1_rate = value.get("fixing1_rate")
        fixing1_volume = value.get("fixing1_volume")
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
        response = requests.get(DATA_URL_TEMPLATE.format((date - datetime.timedelta(days=1)).strftime("%d-%m-%Y")))
        _LOGGER.debug("Downloaded TGE data for date {} [{}]: {}", date, response.status_code, response.text)
        if response.status_code != 200:
            _LOGGER.error("Failed to download TGE data: {}", response.status_code)
            raise TgeException("Failed to download TGE data")
        parser = BeautifulSoup(response.text, "html.parser")
        date_of_data = TgeConnector._get_date_of_data(parser)
        if date != date_of_data:
            return None
        data = TgeConnector._parse_timetable(parser, date)
        return TgeDayData(date, data)

    @staticmethod
    def _get_date_of_data(html_parser: Tag) -> datetime.date:
        # Search for small in h4 in 4-th 'section' of body
        el = html_parser.select_one("body > section:nth-of-type(4) h4 small")
        if el is None:
            raise TgeException("Date of delivery not found on TGE website")
        # np. el.text == "dla dostawy w dniu 08-08-2025 r."
        # Remove prefix and " r."
        date_text = el.get_text(strip=True) \
            .replace("dla dostawy w dniu ", "") \
            .replace(" r.", "") 
        return datetime.datetime.strptime(date_text, "%d-%m-%Y").date()

    @staticmethod
    def _parse_timetable(html_parser: Tag, date_of_data: datetime.date) -> list[TgeHourData]:
        return list(
            map(lambda row: TgeConnector._parse_row(row, date_of_data), TgeConnector._get_rows_of_table(html_parser)))

    @staticmethod
    def _get_rows_of_table(html_parser: Tag) -> list[Tag]:
        valid_pattern = r"^\d\d?-\d\d?$"
        all_rows = html_parser.select("#footable_kontrakty_godzinowe > tbody")[0].select("tr")
        filtered_rows = list(filter(lambda r: re.match(valid_pattern, r.select("td")[0].text.strip()), all_rows))
        return filtered_rows

    @staticmethod
    def _parse_row(row: Tag, date_of_data: datetime.date) -> TgeHourData:
        time_of_row = TgeConnector._get_time_of_row(row, date_of_data)
        fixing1_rate = TgeConnector._get_float_from_column(row, 1)
        fixing1_volume = TgeConnector._get_float_from_column(row, 2)
        fixing2_rate = TgeConnector._get_float_from_column(row, 3)
        fixing2_volume = TgeConnector._get_float_from_column(row, 4)
        return TgeHourData(time_of_row, fixing1_rate, fixing1_volume, fixing2_rate, fixing2_volume)

    @staticmethod
    def _get_time_of_row(row: Tag, date_of_data: datetime.date) -> datetime:
        timezone = datetime.datetime.now().astimezone().tzinfo
        from_to = row.select("td")[0].text.strip().split("-")
        from_time = datetime.time(hour=int(from_to[0]))
        datetime_from = datetime.datetime.combine(date_of_data, from_time, timezone)
        return datetime_from

    @staticmethod
    def _get_float_from_column(row: Tag, number: int) -> float:
        return TgeConnector._parse_float(TgeConnector._get_column_with_number(row, number), 0)

    @staticmethod
    def _get_column_with_number(row: Tag, number: int) -> str:
        return row.select("td")[number].text.strip()

    @staticmethod
    def _parse_float(value: str, default: float) -> float:
        try:
            return float(value.replace(" ", "").replace(",", "."))
        except ValueError:
            return default


if __name__ == '__main__':
    print(TgeConnector.get_data())
