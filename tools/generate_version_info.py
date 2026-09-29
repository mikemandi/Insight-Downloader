from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "app" / "__init__.py"
OUTPUT = ROOT / "installer" / "windows_version_info.txt"

match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', INIT.read_text(encoding="utf-8"))
if not match:
    raise SystemExit("Could not read __version__")

version = match.group(1)
parts = version.split(".")
if len(parts) != 3 or not all(part.isdigit() for part in parts):
    raise SystemExit("Windows build version must be numeric MAJOR.MINOR.PATCH")
major, minor, patch = map(int, parts)

OUTPUT.write_text(
f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, 0),
    prodvers=({major}, {minor}, {patch}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [
          StringStruct(u'CompanyName', u'Insight Development'),
          StringStruct(u'FileDescription', u'Insight Downloader'),
          StringStruct(u'FileVersion', u'{version}'),
          StringStruct(u'InternalName', u'Insight Downloader'),
          StringStruct(u'LegalCopyright', u'Copyright © 2026 Insight Development'),
          StringStruct(u'OriginalFilename', u'Insight Downloader.exe'),
          StringStruct(u'ProductName', u'Insight Downloader'),
          StringStruct(u'ProductVersion', u'{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
''',
encoding="utf-8",
)
print(version)
