r"""
created: 20260816

Scan assets/ for the days missing per year and write the results to README.md.

Usage:
    PS > python3 .\check_missing.py
"""

import argparse
import datetime
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"
README = ROOT / "README.md"
SECTION_TITLE = "## 404 Days"

YEAR_START_OVERRIDE = {2015: datetime.date(2015, 2, 18)}
_URL_TEMPLATE = "https://img.owspace.com/Public/uploads/Download/{year}/{mmdd}.jpg"


def iter_expected_days(year: int):
    start = YEAR_START_OVERRIDE.get(year, datetime.date(year, 1, 1))
    end = datetime.date(year, 12, 31)
    day = start
    while day <= end:
        yield day
        day += datetime.timedelta(days=1)


def collect_missing():
    missing = []
    year_dirs = sorted(p.name for p in ASSETS_DIR.iterdir() if p.is_dir())
    for year in year_dirs:
        try:
            y = int(year)
        except ValueError:
            continue
        year_dir = ASSETS_DIR / year
        existing = {p.stem for p in year_dir.glob("*.jpg")}
        for day in iter_expected_days(y):
            mmdd = day.strftime("%m%d")
            if mmdd not in existing:
                missing.append(
                    {
                        "year": year,
                        "name": f"{mmdd}.jpg",
                        "url": _URL_TEMPLATE.format(year=year, mmdd=mmdd),
                    }
                )
    return missing


def _section_exists() -> bool:
    return SECTION_TITLE in README.read_text(encoding="utf-8") if README.exists() else False


def _replace_section(content: str, table: str) -> str:
    if not _section_exists():
        return f"{content.rstrip()}\n\n## 404 Days\n\n{table}\n"
    before, _ = content.split(SECTION_TITLE, 1)
    return f"{before.rstrip()}\n\n## 404 Days\n\n{table}\n"


def build_table(missing) -> str:
    if not missing:
        return "No missing images found.\n"
    lines = ["| Year | Name | URL |", "| --- | --- | --- |"]
    lines.extend(f"| {m['year']} | `{m['name']}` | {m['url']} |" for m in missing)
    return "\n".join(lines) + "\n"


def verify_missing(missing) -> None:
    import requests

    for m in missing:
        response = requests.get(m["url"], timeout=10)
        if response.status_code == 200:
            print(f"OK (found on server): {m['url']}")
        else:
            print(f"404 (confirmed): {m['url']}")


def download_missing(missing, attempts: int = 3, delay: float = 2.0, backoff: float = 2.0) -> int:
    import requests

    headers = {"Referer": "http://www.owspace.com/"}
    succeeded = 0
    for m in missing:
        target = ASSETS_DIR / m["year"] / m["name"]
        target.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(1, attempts + 1):
            try:
                response = requests.get(m["url"], headers=headers, timeout=30)
                if response.status_code == 200:
                    target.write_bytes(response.content)
                    print(f"Downloaded {m['year']}/{m['name']}")
                    succeeded += 1
                    break
                print(f"Attempt {attempt}/{attempts}: HTTP {response.status_code} for {m['url']}")
            except requests.RequestException as exc:
                print(f"Attempt {attempt}/{attempts}: {exc} for {m['url']}")
            if attempt < attempts:
                time.sleep(delay * (backoff ** (attempt - 1)))
    return succeeded


def main() -> None:
    parser = argparse.ArgumentParser(description="Report missing calendar images to README.md")
    parser.add_argument("-v", "--verify", action="store_true", help="check each missing URL on the server")
    parser.add_argument(
        "-d",
        "--download",
        action="store_true",
        help="download missing images into assets/ (with retries)",
    )
    parser.add_argument("--attempts", type=int, default=3, help="max download attempts per image")
    parser.add_argument("--delay", type=float, default=2.0, help="base delay between attempts (seconds)")
    args = parser.parse_args()

    os.makedirs(ASSETS_DIR, exist_ok=True)
    missing = collect_missing()
    table = build_table(missing)
    content = README.read_text(encoding="utf-8") if README.exists() else "# Owspace Calendar 单向历\n"
    README.write_text(_replace_section(content, table), encoding="utf-8")
    print(f"Missing entries: {len(missing)}")

    if args.download and missing:
        succeeded = download_missing(missing, attempts=args.attempts, delay=args.delay)
        print(f"Downloaded {succeeded}/{len(missing)} missing images")
    elif args.verify:
        verify_missing(missing)
    else:
        sys.exit(0 if not missing else 1)


if __name__ == "__main__":
    main()
