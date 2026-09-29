from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
import winreg
from pathlib import Path


def _wait_for_process(pid: int, timeout_ms: int = 120_000) -> None:
    if os.name != "nt":
        deadline = time.time() + timeout_ms / 1000
        while time.time() < deadline:
            try:
                os.kill(pid, 0)
            except OSError:
                return
            time.sleep(0.25)
        return

    SYNCHRONIZE = 0x00100000
    WAIT_TIMEOUT = 0x00000102
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
    if not handle:
        return
    try:
        result = kernel32.WaitForSingleObject(handle, timeout_ms)
        if result == WAIT_TIMEOUT:
            time.sleep(1)
    finally:
        kernel32.CloseHandle(handle)


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive, "r") as zf:
        for member in zf.infolist():
            target = (destination / member.filename).resolve()
            if destination not in target.parents and target != destination:
                raise RuntimeError(f"Недопустимый путь в ZIP: {member.filename}")
        zf.extractall(destination)


def _copy_payload(staging: Path, target: Path) -> None:
    for item in staging.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(item, destination)


def _show_error(message: str) -> None:
    try:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(0, message, "Insight Downloader Updater", 0x10)
    except Exception:
        pass


def _write_log(message: str) -> None:
    try:
        base = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "Insight Downloader"
        base.mkdir(parents=True, exist_ok=True)
        with (base / "updater.log").open("a", encoding="utf-8") as stream:
            stream.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except Exception:
        pass


def _update_uninstall_version(version: str) -> None:
    if os.name != "nt":
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{6D327C95-E67D-49D5-8EF9-20A7785D98B6}_is1"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, version)
            parts = version.split(".")
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                winreg.SetValueEx(key, "VersionMajor", 0, winreg.REG_DWORD, int(parts[0]))
                winreg.SetValueEx(key, "VersionMinor", 0, winreg.REG_DWORD, int(parts[1]))
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--exe", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    archive = Path(args.archive).resolve()
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    _wait_for_process(args.pid)
    time.sleep(0.4)

    staging = Path(tempfile.mkdtemp(prefix="InsightDownloaderUpdate-"))
    try:
        _safe_extract(archive, staging)
        _copy_payload(staging, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        try:
            archive.unlink(missing_ok=True)
        except Exception:
            pass

    _update_uninstall_version(args.version)

    exe = target / args.exe
    if exe.is_file():
        subprocess.Popen([str(exe)], cwd=str(target), close_fds=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        message = f"Не удалось установить обновление: {exc}"
        _write_log(message)
        _show_error(message)
        raise SystemExit(1)
