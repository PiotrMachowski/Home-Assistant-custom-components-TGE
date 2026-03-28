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
        _LOGGER.debug("Downloading TGE data for date %s...", date)
        response = requests.get(DATA_URL_TEMPLATE.format((date - datetime.timedelta(days=1)).strftime("%d-%m-%Y")))
        _LOGGER.debug("Downloaded TGE data for date %s [%s]: %s", date, response.status_code, response.text)
        if response.status_code != 200:
            _LOGGER.error("Failed to download TGE data: %s", response.status_code)
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
    def _get_date_of_data(html_parser: Tag) -> datetime.date:
        """Extract date from first cell of first data row in RDN table."""
        rows = TgeConnector._get_rows_of_table(html_parser)
        if len(rows) == 0:
            _LOGGER.error("No date of data found - no rows in table")
            raise TgeException("No date of data found")
        
        first_row_text = rows[0].select("td")[0].text.strip()
        # Extract date from format like "2026-03-29_H01" or "2026-03-29_Q00:15"
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", first_row_text)
        if not date_match:
            _LOGGER.error("No date of data found in first row: %s", first_row_text)
            raise TgeException("No date of data found")
        
        date = datetime.datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        return date

    @staticmethod
    def _parse_timetable(html_parser: Tag, date_of_data: datetime.date) -> list[TgeHourData]:
        return list(
            map(lambda row: TgeConnector._parse_row(row, date_of_data), TgeConnector._get_rows_of_table(html_parser)))

    @staticmethod
    def _get_rows_of_table(html_parser: Tag) -> list[Tag]:
        """Get rows from RDN table (new format with id #rdn)."""
        tables = html_parser.select("#rdn tbody")
        if len(tables) == 0:
            _LOGGER.warning("RDN table not found, trying legacy table format")
            # Fallback to old format
            tables = html_parser.select("#footable_kontrakty_godzinowe > tbody")
        
        if len(tables) == 0:
            _LOGGER.error("No table found")
            return []
        
        all_rows = tables[0].select("tr")
        return all_rows

    @staticmethod
    def _parse_row(row: Tag, date_of_data: datetime.date) -> TgeHourData:
        time_of_row = TgeConnector._get_time_of_row(row, date_of_data)
        # New RDN format: Fixing I columns are 2-3, Fixing II columns are 6-7
        fixing1_rate = TgeConnector._get_float_from_column(row, 2)
        fixing1_volume = TgeConnector._get_float_from_column(row, 3)
        fixing2_rate = TgeConnector._get_float_from_column(row, 6)
        fixing2_volume = TgeConnector._get_float_from_column(row, 7)
        return TgeHourData(time_of_row, fixing1_rate, fixing1_volume, fixing2_rate, fixing2_volume)

    @staticmethod
    def _get_time_of_row(row: Tag, date_of_data: datetime.date) -> datetime.datetime:
        """Extract time from first column which contains format like 'H01', 'Q00:15', etc."""
        timezone = datetime.datetime.now().astimezone().tzinfo
        time_text = row.select("td")[0].text.strip()
        
        # Parse time from format: "2026-03-29_H01" or "2026-03-29_Q00:15"
        # Extract just the time part (H01 or Q00:15)
        time_match = re.search(r"_([HQ])(.+?)$", time_text)
        if not time_match:
            _LOGGER.error("Could not parse time from: %s", time_text)
            raise TgeException(f"Could not parse time from: {time_text}")
        
        time_type = time_match.group(1)
        time_value = time_match.group(2)
        
        if time_type == 'H':
            # Hourly format: H01, H02, ..., H24
            hour = int(time_value)
            # H24 represents the last hour (23:00-24:00), convert to hour 23
            if hour == 24:
                hour = 23
            from_time = datetime.time(hour=hour)
        elif time_type == 'Q':
            # Quarterly format: Q00:15, Q00:30, Q00:45, Q01:00, etc.
            # Handle edge case Q24:00 by converting to 23:59
            time_parts = time_value.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # Validate and fix hour is in valid range
            if hour > 23:
                _LOGGER.warning("Invalid hour %d in time: %s, converting to 23:59", hour, time_text)
                hour = 23
                minute = 59
            
            from_time = datetime.time(hour=hour, minute=minute)
        else:
            raise TgeException(f"Unknown time format: {time_text}")
        
        datetime_from = datetime.datetime.combine(date_of_data, from_time, timezone)
        return datetime_from

    @staticmethod
    def _get_float_from_column(row: Tag, number: int) -> float:
        return TgeConnector._parse_float(TgeConnector._get_column_with_number(row, number), 0)

    @staticmethod
    def _get_column_with_number(row: Tag, number: int) -> str:
        cells = row.select("td")
        if number >= len(cells):
            _LOGGER.warning("Column %d not found in row (only %d cells)", number, len(cells))
            return ""
        return cells[number].text.strip()

    @staticmethod
    def _parse_float(value: str, default: float) -> float:
        try:
            # Handle "-" and empty values
            if value == "-" or value == "" or value.strip() == "-":
                return default
            return float(value.replace(" ", "").replace(",", "."))
        except ValueError:
            _LOGGER.warning("Could not parse float from: %s", value)
            return default


if __name__ == '__main__':
    print(TgeConnector.get_data())
