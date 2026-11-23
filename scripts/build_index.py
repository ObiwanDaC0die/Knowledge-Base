#!/usr/bin/env python3
"""Build the Knowledge Library's deterministic HTML document index."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "index.json"


def filename_title(path: str | Path) -> str:
    """Turn a snake_case or kebab-case filename into a readable title."""
    words = re.split(r"[_\-\s]+", Path(path).stem)
    return " ".join(word[:1].upper() + word[1:] for word in words if word)


class DocumentMetadata(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.description = ""
        self.tags: list[str] = []
        self.keywords: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "").strip() for key, value in attrs}
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "meta":
            key = (values.get("name") or values.get("property") or "").lower()
            content = values.get("content", "")
            if key in {"description", "og:description"} and content and not self.description:
                self.description = content
            elif key in {"tags", "tag", "article:tag"}:
                self.tags.extend(split_terms(content))
            elif key == "keywords":
                self.keywords.extend(split_terms(content))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def split_terms(value: str) -> list[str]:
    seen: set[str] = set()
    terms: list[str] = []
    for item in re.split(r"[,;|]", value):
        term = " ".join(item.split())
        key = term.casefold()
        if term and key not in seen:
            seen.add(key)
            terms.append(term)
    return terms


def stable_id(relative_path: str) -> str:
    """IDs depend on path, so title or metadata edits do not break favorites."""
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]


def extract_metadata(path: Path, relative_path: str) -> dict[str, Any]:
    parser = DocumentMetadata()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    title = " ".join(" ".join(parser.title_parts).split()) or filename_title(path.name)
    return {"id": stable_id(relative_path), "title": title, "path": relative_path,
            "tags": parser.tags, "keywords": parser.keywords, "description": parser.description}


def discover_documents(root: Path = ROOT) -> list[dict[str, Any]]:
    documents = []
    for path in sorted(root.rglob("*.html")):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts) or relative.name.lower() == "index.html":
            continue
        documents.append(extract_metadata(path, relative.as_posix()))
    documents.sort(key=lambda item: (item["title"].casefold(), item["path"].casefold()))
    return documents


def build_index(root: Path = ROOT, generated_at: str | None = None) -> dict[str, Any]:
    return {"generatedAt": generated_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "documents": discover_documents(root)}


def main() -> None:
    payload = build_index()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} with {len(payload['documents'])} documents")


if __name__ == "__main__":
    main()
