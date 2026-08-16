"""
created: 20230705

## Usage

```
PS > python3 .\main.py --help
usage: Get calendar [-h] [-t] {2015,2016,2017,2018,2019,2020,2021,2022}

Get calendar from owspace

positional arguments:
  {2015,2016,2017,2018,2019,2020,2021,2022}

options:
  -h, --help            show this help message and exit
  -t, --thread
```
"""

import argparse
import datetime
import os
import re
import threading
import time

import requests

headers = {"Referer": "http://www.owspace.com/"}


def init_url_pool(year):
    if year == 2015:
        start = datetime.datetime(2015, 2, 18)
    else:
        start = datetime.datetime(year, 1, 1)
    end = datetime.datetime(year, 12, 31)
    return get_url_pool_within_days(start, end)


def get_url_pool_within_days(start, end):
    url_pool = []
    while start <= end:
        url_address = (
            "https://img.owspace.com/Public/uploads/Download/"
            + start.strftime("%Y/%m%d.jpg")
        )
        url_pool.append(url_address)
        start += datetime.timedelta(days=1)
    return url_pool


def download_serial_owspace(url_pool, output_dir):
    for url in url_pool:
        regex = re.search(r"(\d{4})/(\d{2})(\d{2})(\.jpg)", url)
        year = regex.group(1)
        month = regex.group(2)
        day = regex.group(3)
        suffix = regex.group(4)
        file_name = output_dir + "/" + month + day + suffix
        timestamp = time.mktime((int(year), int(month), int(day), 0, 0, 0, 0, 0, 0))

        download_image_with_customed_date(url, file_name, timestamp)


def download_image_with_customed_date(url, file_name, timestamp):
    response = requests.get(url, headers)
    if response.status_code == 200:
        access_time = timestamp
        modified_time = timestamp
        with open(file_name, "wb") as f:
            f.write(response.content)
            os.utime(file_name, (access_time, modified_time))
        print(f"Downloaded {file_name}")
    else:
        print(f"Failed when download {file_name}")


def download_threads_owspace(url_pool, output_dir):
    threads = []

    for url in url_pool:
        regex = re.search(r"(\d{4})/(\d{2})(\d{2})(\.jpg)", url)
        year = regex.group(1)
        month = regex.group(2)
        day = regex.group(3)
        suffix = regex.group(4)
        file_name = output_dir + "/" + month + day + suffix
        timestamp = time.mktime((int(year), int(month), int(day), 0, 0, 0, 0, 0, 0))

        thread = threading.Thread(
            target=download_image_with_customed_date, args=(url, file_name, timestamp)
        )
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    now_year = datetime.datetime.today().year
    parser = argparse.ArgumentParser(
        prog="Get calendar", description="Get calendar from owspace"
    )
    parser.add_argument("year", type=int, choices=range(2015, now_year))
    parser.add_argument("-t", "--thread", action="store_true", required=False)
    args = parser.parse_args()

    output_dir = "assets/" + str(args.year)
    url_pool = init_url_pool(args.year)

    os.makedirs(output_dir, exist_ok=True)
    if args.thread is False:
        download_serial_owspace(url_pool, output_dir)
    else:
        download_threads_owspace(url_pool, output_dir)
