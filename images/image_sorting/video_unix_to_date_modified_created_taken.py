import os
import sys
import shutil
import subprocess
from datetime import datetime, timezone

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".3gp", ".webm", ".mts", ".m2ts", ".wmv"}
TOLERANCE = 2  # seconds; covers FAT/exFAT's 2-second granularity

EXIFTOOL = shutil.which("exiftool")
FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


def parse_unix_name(stem):
    """Return a unix timestamp in seconds, or None if the name isn't one."""
    if not stem.isdigit():
        return None
    n = int(stem)
    if len(stem) == 13:       # milliseconds
        return n / 1000
    if len(stem) == 10:       # seconds
        return float(n)
    return None


# ---------- file system times ----------

def get_created_time(st):
    """Creation time on Windows (birth time elsewhere if available), else None."""
    birth = getattr(st, "st_birthtime", None)
    if birth is not None:
        return birth
    if os.name == "nt":
        return st.st_ctime
    return None  # Linux: creation time not reliably available/settable


def fs_times_ok(path, ts):
    st = os.stat(path)
    if abs(st.st_mtime - ts) > TOLERANCE:
        return False
    if os.name == "nt":
        created = get_created_time(st)
        if created is None or abs(created - ts) > TOLERANCE:
            return False
    return True


def set_windows_times(path, ts):
    """Set created, accessed and modified times on Windows."""
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                wintypes.HANDLE]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.SetFileTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                                ctypes.POINTER(wintypes.FILETIME),
                                ctypes.POINTER(wintypes.FILETIME)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    ft = int(ts * 10_000_000) + 116444736000000000  # 100ns ticks since 1601
    filetime = wintypes.FILETIME(ft & 0xFFFFFFFF, ft >> 32)

    FILE_WRITE_ATTRIBUTES = 0x100
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    handle = k32.CreateFileW(path, FILE_WRITE_ATTRIBUTES, 0, None,
                             OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None)
    if handle in (None, wintypes.HANDLE(-1).value):
        raise OSError("Could not open file to set times")
    try:
        if not k32.SetFileTime(handle, ctypes.byref(filetime),
                               ctypes.byref(filetime), ctypes.byref(filetime)):
            raise OSError("SetFileTime failed")
    finally:
        k32.CloseHandle(handle)


def set_fs_times(path, ts):
    os.utime(path, (ts, ts))  # accessed + modified
    if os.name == "nt":
        set_windows_times(path, ts)  # created


# ---------- embedded metadata ----------

def have_meta_tool():
    return bool(EXIFTOOL or FFMPEG)


def embedded_ok(path, dt):
    """True if embedded date already matches, False if not, None if can't check."""
    stamp = dt.strftime("%Y:%m:%d %H:%M:%S")

    if EXIFTOOL:
        r = subprocess.run(
            [EXIFTOOL, "-s3", "-QuickTime:CreateDate", "-QuickTime:MediaCreateDate",
             "-QuickTime:ModifyDate", path],
            capture_output=True, text=True)
        if r.returncode != 0:
            return False
        lines = [l.strip()[:19] for l in r.stdout.splitlines() if l.strip()]
        return len(lines) == 3 and all(l == stamp for l in lines)

    if FFPROBE:
        r = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format_tags=creation_time",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True)
        out = r.stdout.strip()
        if not out:
            return False
        try:
            found = datetime.strptime(out[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return False
        return abs((found - dt.replace(tzinfo=None)).total_seconds()) <= TOLERANCE

    return None  # ffmpeg only, no ffprobe: can't verify, so we'll just write


def set_embedded_metadata(path, dt):
    """Write 'date taken' style metadata inside the video. Returns True on success."""
    if EXIFTOOL:
        stamp = dt.strftime("%Y:%m:%d %H:%M:%S")
        cmd = [EXIFTOOL, "-overwrite_original",
               f"-AllDates={stamp}",
               f"-QuickTime:CreateDate={stamp}", f"-QuickTime:ModifyDate={stamp}",
               f"-QuickTime:TrackCreateDate={stamp}", f"-QuickTime:TrackModifyDate={stamp}",
               f"-QuickTime:MediaCreateDate={stamp}", f"-QuickTime:MediaModifyDate={stamp}",
               path]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r.returncode == 0

    if FFMPEG:
        base, ext = os.path.splitext(path)
        tmp = base + ".tmp_meta" + ext
        iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-i", path, "-map", "0",
               "-c", "copy", "-metadata", f"creation_time={iso}", tmp]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            os.replace(tmp, path)
            return True
        if os.path.exists(tmp):
            os.remove(tmp)
    return False


# ---------- main ----------

def main():
    folder = input("Enter folder path: ").strip().strip('"').strip("'")
    folder = os.path.expanduser(folder)
    if not os.path.isdir(folder):
        print("That folder doesn't exist.")
        sys.exit(1)

    if not have_meta_tool():
        print("Note: neither exiftool nor ffmpeg found, so 'date taken' metadata "
              "will be skipped (file system dates will still be set).\n")

    done = skipped = 0

    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        stem, ext = os.path.splitext(name)
        if not os.path.isfile(path) or ext.lower() not in VIDEO_EXTS:
            continue

        ts = parse_unix_name(stem)
        if ts is None:
            print(f"SKIP  {name} (name isn't a unix timestamp)")
            continue

        dt = datetime.fromtimestamp(ts, tz=timezone.utc)

        fs_ok = fs_times_ok(path, ts)
        meta_state = embedded_ok(path, dt) if have_meta_tool() else True  # True = nothing to do

        if fs_ok and meta_state is not False and meta_state is not None:
            print(f"OK    {name} already correct, skipped")
            skipped += 1
            continue

        actions = []
        # Embedded metadata first (rewriting the file resets its times)
        if have_meta_tool() and meta_state in (False, None):
            ok = set_embedded_metadata(path, dt)
            actions.append("metadata" if ok else "metadata FAILED")
            fs_ok = False  # file was rewritten, so re-apply fs times

        if not fs_ok:
            set_fs_times(path, ts)
            actions.append("file times")

        print(f"FIXED {name} -> {dt:%Y-%m-%d %H:%M:%S} UTC ({', '.join(actions)})")
        done += 1

    print(f"\nDone. Fixed: {done}, already correct: {skipped}")


if __name__ == "__main__":
    main()