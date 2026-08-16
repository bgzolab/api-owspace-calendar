r"""
created: 20260816

Daily maintenance job for CI:
  1. Pull the next few days of the current year into assets/<year>/.
  2. Refresh the "Today:" relative link under the README h1.

Usage:
    PS > python3 .\src\update_daily.py
"""

import argparse
import datetime
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
README = ROOT / "README.md"

_HEADERS = {"Referer": "http://www.owspace.com/"}
_URL_TEMPLATE = "https://img.owspace.com/Public/uploads/Download/{year}/{mmdd}.jpg"
_FILENAME_RE = re.compile(r"^(\d{2})(\d{2})\.jpg$")

_TODAY_RE = re.compile(
    r"^!\[Placeholder-\d{4}-\d{2}-\d{2}\]\(assets/\d{4}/\d{4}\.jpg\)\s*$",
    re.MULTILINE,
)
_TITLE_LINE = "# Owspace Calendar"


def _iter_days(start: datetime.date, end: datetime.date):
    day = start
    while day <= end:
        yield day
        day += datetime.timedelta(days=1)


def latest_date(year: int) -> datetime.date | None:
    year_dir = ASSETS_DIR / str(year)
    if not year_dir.is_dir():
        return None
    latest = None
    for path in year_dir.glob("*.jpg"):
        match = _FILENAME_RE.match(path.name)
        if not match:
            continue
        try:
            day = datetime.date(year, int(match.group(1)), int(match.group(2)))
        except ValueError:
            continue
        if latest is None or day > latest:
            latest = day
    return latest


def _download(url: str, target: Path, day: datetime.date) -> bool:
    import requests

    try:
        response = requests.get(url, headers=_HEADERS, timeout=30)
        if response.status_code != 200:
            print(f"HTTP {response.status_code}: {url}")
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        timestamp = time.mktime((day.year, day.month, day.day, 0, 0, 0, 0, 0, 0))
        os.utime(target, (timestamp, timestamp))
        print(f"Downloaded {target.relative_to(ROOT)}")
        return True
    except requests.RequestException as exc:
        print(f"Request error: {exc} ({url})")
        return False


def pull_days(
    year: int, days: int, max_failures: int, start_from: datetime.date | None = None
) -> int:
    start = start_from or latest_date(year)
    if start is None:
        start = datetime.date.today()
    else:
        start = start + datetime.timedelta(days=1)
    end = min(start + datetime.timedelta(days=days - 1), datetime.date(year, 12, 31))

    pulled = 0
    consecutive_failures = 0
    for day in _iter_days(start, end):
        target = ASSETS_DIR / str(year) / f"{day:%m%d}.jpg"
        if target.exists():
            consecutive_failures = 0
            continue
        url = _URL_TEMPLATE.format(year=year, mmdd=day.strftime("%m%d"))
        if _download(url, target, day):
            pulled += 1
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                print(f"Stopping after {max_failures} consecutive failures")
                break
    return pulled


def _today_link(day: datetime.date) -> str:
    return f"![Placeholder-{day:%Y-%m-%d}](assets/{day:%Y}/{day:%m%d}.jpg)"


def update_readme(day: datetime.date) -> None:
    if not README.exists():
        return
    content = README.read_text(encoding="utf-8")
    link = _today_link(day) + "\n"
    if _TODAY_RE.search(content):
        content = _TODAY_RE.sub(link, content, count=1)
    else:
        lines = content.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.rstrip("\r\n") == _TITLE_LINE:
                lines.insert(index + 1, link)
                break
        content = "".join(lines)
    README.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pull the current year's calendar forward and refresh the README today link"
    )
    parser.add_argument("--year", type=int, default=datetime.date.today().year)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max-failures", type=int, default=1)
    args = parser.parse_args()

    pulled = pull_days(args.year, args.days, args.max_failures)
    today = datetime.date.today()
    if today.year == args.year:
        update_readme(today)
    print(f"Pulled {pulled} new images for {args.year}")


if __name__ == "__main__":
    main()
