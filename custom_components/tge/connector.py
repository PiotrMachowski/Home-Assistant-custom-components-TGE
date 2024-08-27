"""Connector for TGE integration."""

import datetime
import logging
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup, ResultSet, Tag

from .const import URL

_LOGGER = logging.getLogger(__name__)


@dataclass
class TgeHourData:
    time: datetime.datetime
    fixing1_rate: float
    fixing1_volume: float
    fixing2_rate: float
    fixing2_volume: float


@dataclass
class TgeData:
    date: datetime.date
    hours: list[TgeHourData]


@dataclass
class TgeException(Exception):
    msg: str


class TgeConnector:

    @staticmethod
    def get_data() -> TgeData:
        _LOGGER.debug("Downloading TGE data...")
        response = requests.get(URL)
        _LOGGER.debug("Downloaded TGE data {}: {}", response.status_code, response.text)
        if response.status_code != 200:
            _LOGGER.error("Failed to download TGE data: {}", response.status_code)
            raise TgeException("Failed to download TGE data")
        parser = BeautifulSoup(response.text, "html.parser")
        date = TgeConnector._get_date_of_data(parser)
        data = TgeConnector._parse_timetable(parser, date)
        return TgeData(date, data)

    @staticmethod
    def _get_date_of_data(html_parser: Tag) -> datetime.date:
        date_text = html_parser.select("body")[0].select("section")[4].select("small")[0].text.strip().replace(
            "dla dostawy w dniu ", "")
        date = datetime.datetime.strptime(date_text, "%d-%m-%Y").date()
        return date

    @staticmethod
    def _parse_timetable(html_parser: Tag, date_of_data: datetime.date) -> list[TgeHourData]:
        return list(
            map(lambda row: TgeConnector._parse_row(row, date_of_data), TgeConnector._get_rows_of_table(html_parser)))

    @staticmethod
    def _get_rows_of_table(html_parser: Tag) -> ResultSet[Tag]:
        return html_parser.select("#footable_kontrakty_godzinowe > tbody")[0].select("tr")

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
    def _get_fixing1_rate(row: Tag) -> float:
        return float(TgeConnector._get_column_with_number(row, 1).replace(",", "."))

    @staticmethod
    def _get_fixing1_volume(row: Tag) -> float:
        return float(TgeConnector._get_column_with_number(row, 2).replace(",", "."))

    @staticmethod
    def _get_float_from_column(row: Tag, number: int) -> float:
        return float(TgeConnector._get_column_with_number(row, number).replace(",", "."))

    @staticmethod
    def _get_column_with_number(row: Tag, number: int) -> str:
        return row.select("td")[number].text.strip()


if __name__ == '__main__':
    print(TgeConnector.get_data())
