from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.version import Version

if len(sys.argv) != 2:
    raise SystemExit("Usage: python tools/set_version.py 0.6.1")

version = str(Version(sys.argv[1]))
if any(ch in version for ch in "+-"):
    raise SystemExit("Use numeric MAJOR.MINOR.PATCH for Windows releases")

root = Path(__file__).resolve().parents[1]
init_file = root / "app" / "__init__.py"
pyproject = root / "pyproject.toml"

init_file.write_text(f'__version__ = "{version}"\n', encoding="utf-8")
text = pyproject.read_text(encoding="utf-8")
text = re.sub(r'(?m)^version\s*=\s*"[^"]+"', f'version = "{version}"', text, count=1)
pyproject.write_text(text, encoding="utf-8")
print(f"Version set to {version}")
