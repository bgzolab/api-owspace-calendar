r"""
created: 20230705

## Usage

```
PS > python3 .\src\owspace-calendar-downloader.py --help
usage: Get calendar [-h] [-t] {2015,2016,...,2026}

Get calendar from owspace
```
"""

import argparse
import datetime
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent

_HEADERS = {"Referer": "http://www.owspace.com/"}
_URL_TEMPLATE = "https://img.owspace.com/Public/uploads/Download/{year}/{mmdd}.jpg"
_DATE_PATTERN = re.compile(r"(\d{4})/(\d{2})(\d{2})\.jpg")


@dataclass(frozen=True)
class _Image:
    url: str
    file_name: str
    timestamp: float


def _init_url_pool(year: int) -> list[str]:
    start = (
        datetime.datetime(2015, 2, 18)
        if year == 2015
        else datetime.datetime(year, 1, 1)
    )
    end = datetime.datetime(year, 12, 31)
    return [
        _URL_TEMPLATE.format(year=day.strftime("%Y"), mmdd=day.strftime("%m%d"))
        for day in _iter_days(start, end)
    ]


def _iter_days(start: datetime.datetime, end: datetime.datetime):
    day = start
    while day <= end:
        yield day
        day += datetime.timedelta(days=1)


def _build_image(url: str, output_dir: str) -> _Image:
    match = _DATE_PATTERN.search(url)
    if match is None:
        raise ValueError(f"Unrecognized URL: {url}")
    year, month, day = match.groups()
    file_name = os.path.join(output_dir, f"{month}{day}.jpg")
    timestamp = time.mktime((int(year), int(month), int(day), 0, 0, 0, 0, 0, 0))
    return _Image(url=url, file_name=file_name, timestamp=timestamp)


def _download_image(image: _Image) -> None:
    response = requests.get(image.url, headers=_HEADERS, timeout=30)
    if response.status_code != 200:
        print(f"Failed when download {image.file_name}")
        return
    with open(image.file_name, "wb") as f:
        f.write(response.content)
    os.utime(image.file_name, (image.timestamp, image.timestamp))
    print(f"Downloaded {image.file_name}")


def download_serial_owspace(url_pool: list[str], output_dir: str) -> None:
    for url in url_pool:
        _download_image(_build_image(url, output_dir))


def download_threads_owspace(
    url_pool: list[str], output_dir: str, max_workers: int = 8
) -> None:
    images = (_build_image(url, output_dir) for url in url_pool)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_download_image, image) for image in images]
        for future in as_completed(futures):
            future.result()


def main() -> None:
    now_year = datetime.datetime.today().year
    parser = argparse.ArgumentParser(
        prog="Get calendar", description="Get calendar from owspace"
    )
    parser.add_argument("year", type=int, choices=range(2015, now_year + 1))
    parser.add_argument("-t", "--thread", action="store_true", required=False)
    args = parser.parse_args()

    output_dir = ROOT / "assets" / str(args.year)
    url_pool = _init_url_pool(args.year)

    os.makedirs(output_dir, exist_ok=True)
    if args.thread:
        download_threads_owspace(url_pool, output_dir)
    else:
        download_serial_owspace(url_pool, output_dir)


if __name__ == "__main__":
    main()
