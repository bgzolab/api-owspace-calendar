# AGENTS.md

Guidance for AI agents and maintainers working in this repository.

## Project

Owspace (单向历) calendar wallpaper downloader and completeness checker.
Images are hosted at `https://img.owspace.com/Public/uploads/Download/{year}/{MMdd}.jpg`.

## Directory structure

```
.
├── assets/            # Calendar wallpapers grouped by year (YYYY/MMdd.jpg)
├── src/
│   ├── owspace-calendar-downloader.py   # Download a whole year
│   └── check_missing.py                 # Detect gaps / backfill / generate the 404 list
└── README.md
```

## Scripts

### owspace-calendar-downloader.py

- Downloads every day of a year into `assets/<year>/`.
- Special case: 2015 starts at Feb 18; all other years start at Jan 1.
- Writes each file then applies `os.utime` so the file's mtime equals its calendar date.
- `-t/--thread` uses a `ThreadPoolExecutor` (8 workers); default is serial.
- Requires `requests`.

### check_missing.py

- Scans every year dir under `assets/`, compares against the expected days, and writes a
  `| Year | Name | URL |` table into README.md under the literal heading `## 404 Days`.
- The README section is replaced on every run. **Important:** the split delimiter is the
  literal string `## 404 Days`, so that string must NOT appear anywhere in the README
  before the section, or content after it gets truncated on rewrite.
- Only checks dates up to today (`end = min(Dec 31, today)`); future dates are not reported.
- Exit code: `0` when nothing is missing, `1` when there are missing entries (CI-friendly).
- `-d/--download`: backfill missing images into `assets/` with retries
  (`--attempts` default 3, exponential backoff from `--delay` default 2.0s).
- `-v/--verify`: issues an HTTP request per missing URL to distinguish a server-side 404
  from a local gap; does NOT modify README.

## Conventions

- All paths resolve from the repository root (scripts use
  `Path(__file__).resolve().parent.parent`).
- Run scripts from the repository root.
- `requests` is the only third-party dependency; it is imported lazily inside
  `verify_missing` / `download_missing`.

## Usage

Run scripts from the repository root. Install the dependency first:

```bash
python -m pip install requests
```

### Download a year

Downloads into `assets/<year>/`:

```powershell
python src/owspace-calendar-downloader.py 2026        # serial
python src/owspace-calendar-downloader.py 2026 -t     # threaded (8 workers)
```

### Check for missing days

Scans `assets/` and writes the missing list into the "404 Days" section of
README.md (idempotent — rerun to refresh):

```powershell
python src/check_missing.py
```

Exit code is `0` when nothing is missing, `1` otherwise.

### Backfill missing images

Downloads missing days into `assets/` with retries:

```powershell
python src/check_missing.py -d
python src/check_missing.py -d --attempts 5 --delay 1
```

### Verify missing URLs

Confirms each gap is a server-side 404 (does not modify README):

```powershell
python src/check_missing.py -v
```
