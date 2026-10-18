"""Read ``params.yaml`` and refuse any input that has no source.

Every number the models use (other than the CODATA constants in
``common.constants``) has to come from one of these files. An entry is valid
only if it has a value, a unit, and a source. The source is either a public
URL or the exact word ASSUMPTION. Assumptions must say, in the note, the range
that was swept, so a reader can see it was not a measured lander value.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Entry:
    """One input, with the citation that lets someone else defend it."""

    name: str
    value: Any
    unit: str
    source: str
    note: str

    @property
    def is_assumption(self) -> bool:
        return self.source.strip().upper() == "ASSUMPTION"


def load_params(path: str | Path) -> dict[str, Entry]:
    """Load a parameter book.

    The YAML shape is a top-level key ``parameters`` whose values are mappings
    with ``value``, ``unit``, ``source`` and ``note``.
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict) or "parameters" not in raw:
        raise ValueError(f"{path} must contain a top-level 'parameters' mapping")

    book: dict[str, Entry] = {}
    for name, item in raw["parameters"].items():
        if not isinstance(item, dict):
            raise ValueError(f"{name} must be a mapping with value, unit, source, note")
        missing = [key for key in ("value", "unit", "source", "note") if key not in item]
        if missing:
            raise ValueError(f"{name} is missing {missing}")
        source = str(item["source"]).strip()
        note = str(item["note"]).strip()
        if source.upper() != "ASSUMPTION" and not source.startswith(("http://", "https://")):
            raise ValueError(
                f"{name} source must be an http(s) URL or ASSUMPTION, got {source!r}"
            )
        if source.upper() == "ASSUMPTION" and "swept" not in note.lower():
            raise ValueError(
                f"{name} is an ASSUMPTION so its note must describe the range swept"
            )
        book[name] = Entry(
            name=name,
            value=item["value"],
            unit=str(item["unit"]),
            source=source,
            note=note,
        )
    return book


def require(book: dict[str, Entry], name: str) -> Entry:
    """Fetch one entry or fail with the file's own key name."""
    try:
        return book[name]
    except KeyError as exc:
        raise KeyError(f"params.yaml has no entry {name!r}") from exc
