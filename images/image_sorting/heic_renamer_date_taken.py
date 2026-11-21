#!/usr/bin/env python3
"""
Rename every file in a folder to its creation date as a Unix timestamp
in milliseconds.

    IMG_0679.HEIC  ->  1767981153000.HEIC

If two files end up with the same timestamp, the milliseconds are simply
incremented (…000, …001, …002) until each name is unique.

Creation date is chosen in this order:
  1. EXIF "date taken" (DateTimeOriginal), for photos. Needs Pillow
     (and pillow-heif for .HEIC):  pip install pillow pillow-heif
  2. File system creation time (Windows, macOS)
  3. File modified time (Linux, which usually doesn't expose creation time)

Works on Windows and Linux. The folder path is entered at the prompt.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from PIL import Image

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        pass
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

EXIF_IFD = 0x8769
TAG_DATETIME = 0x0132
TAG_DATETIME_ORIGINAL = 0x9003
TAG_OFFSET_TIME_ORIGINAL = 0x9011


def exif_timestamp(path: Path):
    """Return the EXIF capture time as a Unix timestamp in ms, or None."""
    if not HAVE_PIL:
        return None
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            ifd = exif.get_ifd(EXIF_IFD)
            raw = ifd.get(TAG_DATETIME_ORIGINAL) or exif.get(TAG_DATETIME)
            if not raw:
                return None
            dt = datetime.strptime(str(raw).strip(), "%Y:%m:%d %H:%M:%S")
            offset = ifd.get(TAG_OFFSET_TIME_ORIGINAL)
            if offset:  # e.g. "+05:30"
                sign = -1 if offset.startswith("-") else 1
                hours, minutes = offset[1:].split(":")
                tz = timezone(sign * timedelta(hours=int(hours), minutes=int(minutes)))
                dt = dt.replace(tzinfo=tz)
            # With no offset, the time is treated as this machine's local time
            return int(dt.timestamp()) * 1000
    except Exception:
        return None


def fs_timestamp(path: Path) -> int:
    """Return the file system creation time in ms (modified time on Linux)."""
    st = path.stat()
    birth = getattr(st, "st_birthtime", None)
    if birth is not None:  # Windows (py3.12+), macOS
        return int(birth * 1000)
    if os.name == "nt":  # older Python on Windows: st_ctime is creation time
        return int(st.st_ctime * 1000)
    return int(st.st_mtime * 1000)  # Linux: no reliable creation time


def get_timestamp(path: Path):
    ts = exif_timestamp(path)
    if ts is not None:
        return ts, "EXIF"
    return fs_timestamp(path), "filesystem"


def unique_target(folder: Path, ts_ms: int, ext: str, taken: set) -> Path:
    """Avoid overwriting: bump the timestamp by 1 ms until the name is free."""
    candidate = folder / f"{ts_ms}{ext}"
    while candidate.exists() or candidate in taken:
        ts_ms += 1
        candidate = folder / f"{ts_ms}{ext}"
    return candidate


def main():
    print("=== Rename files to Unix timestamp ===")
    if not sys.stdin or not sys.stdin.isatty():
        print("Warning: this doesn't look like an interactive terminal, so the "
              "prompt may not work.\nRun it from Command Prompt, PowerShell or a "
              "Linux terminal:  python rename_to_unixtime.py\n")

    raw = input("Enter folder path: ").strip().strip('"').strip("'")
    folder = Path(os.path.expandvars(os.path.expanduser(raw))).resolve()

    if not folder.is_dir():
        sys.exit(f"Not a valid folder: {folder}")

    if not HAVE_PIL:
        print("Note: Pillow not installed, so EXIF dates are skipped "
              "(pip install pillow pillow-heif).\n")

    this_script = Path(__file__).resolve()
    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.resolve() != this_script
    )
    if not files:
        sys.exit("No files found in that folder.")

    plan, taken = [], set()
    for f in files:
        ts, source = get_timestamp(f)
        # Already named correctly (allowing for ms that were bumped on a clash)
        if f.stem.isdigit() and 0 <= int(f.stem) - ts < 1000:
            continue
        target = unique_target(folder, ts, f.suffix, taken)
        taken.add(target)
        plan.append((f, target, source))

    if not plan:
        sys.exit("Nothing to rename.")

    print(f"\nPlanned renames ({len(plan)}):")
    for src, dst, source in plan:
        print(f"  {src.name}  ->  {dst.name}   [{source}]")

    if input("\nProceed? [y/N]: ").strip().lower() != "y":
        sys.exit("Cancelled. No files were changed.")

    done = 0
    for src, dst, _ in plan:
        try:
            src.rename(dst)
            done += 1
        except OSError as e:
            print(f"  Failed: {src.name} ({e})")
    print(f"\nRenamed {done} of {len(plan)} files.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(e.code)
    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        if os.name == "nt":  # keep the window open if launched by double-click
            input("\nPress Enter to close...")