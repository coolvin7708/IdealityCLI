"""
src/utils/fileio.py

Low-level JSON file I/O helpers used by the `store` and `summarize` commands.

Functions:
    write_json(path, data)  — serialise `data` and write to disk.
    read_json(path)         — load and deserialise JSON from disk.
"""

import json
from pathlib import Path


def write_json(path: str | Path, data: list | dict, indent: int = 2) -> None:
    """
    Serialise `data` as JSON and write it to `path`.

    Creates any missing parent directories automatically.

    Args:
        path:   Destination file path (str or Path).
        data:   Python object to serialise (list or dict).
        indent: Number of spaces for pretty-printing (default 2).

    Raises:
        OSError: If the file cannot be written.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=indent, ensure_ascii=False)


def read_json(path: str | Path) -> list | dict:
    """
    Load and return the parsed contents of a JSON file.

    Args:
        path: Source file path (str or Path).

    Returns:
        Python list or dict depending on the file's root element.

    Raises:
        FileNotFoundError: If `path` does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open(encoding="utf-8") as fh:
        return json.load(fh)
