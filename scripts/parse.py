"""
parse.py — Parse the Maududi Tafhim al-Quran djvu text into structured JSON.

Input:  maududi_raw.txt  (djvu OCR output from archive.org)
Output: dist/maududi.json        — full dataset, array of surah objects
        dist/by_surah/{N}.json   — one file per surah

Output schema per surah:
    {
        "surah": 2,
        "name": "Al Baqarah",
        "english_name": "The Cow",
        "introduction": "<full intro text>",
        "verses": [
            {
                "surah": 2,
                "ayah": 255,
                "verse_text": "<Maududi's English rendering of the verse>",
                "commentary": "<footnote text(s) for this verse>"
            }
        ]
    }

Usage:
    uv run python scripts/parse.py
    uv run python scripts/parse.py --surah 1      # single surah, prints JSON to stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = _REPO_ROOT / "maududi_raw.txt"
DIST_DIR = _REPO_ROOT / "dist"
CHAPTERS_DIR = DIST_DIR / "chapters"

# ── Patterns ──────────────────────────────────────────────────────────────────

# Surah header — multiple OCR variants observed in the djvu text:
#   "1. Surah Al Fatihah (The Opening)"   — standard
#   "11. Surah Hud"                        — no English name in parens
#   "40. Surah Al Mu'min (The Believer),"  — trailing comma
#   "44, Surah Ad Dukhan (The Smoke)"      — comma separator instead of period
#   "91. Sura As Shams (The Sun)"          — "Sura" not "Surah"
# Note: Surah 16 header omits "Surah" entirely; handled via _SURAH_HEADER_NO_PREFIX.
_SURAH_HEADER = re.compile(
    r"^(\d{1,3})[.,]\s+Sura[h]?\s+(.+?)(?:\s*\(([^)]+)\))?\s*[,.]?\s*$",
    re.IGNORECASE,
)
# Catches the one outlier: "16. An Nahl (The Honey Bee)"
_SURAH_HEADER_NO_PREFIX = re.compile(
    r"^(16)\.\s+(An Nahl)\s*\(([^)]+)\)\s*$",
    re.IGNORECASE,
)

# Verse marker: "(2:255) In the name of..."
_VERSE_MARKER = re.compile(r"^\((\d{1,3}):(\d{1,3})\)\s*(.*)$")

# Footnote: "1. Some commentary text..." — a digit(s) + period at start of line
_FOOTNOTE_START = re.compile(r"^(\d+)\.\s+(.+)")

# Arabic script block — remove these OCR artifacts entirely
_ARABIC_BLOCK = re.compile(r"[\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeFF]+")

# Repeated page-break noise lines (short lines of symbols / single chars)
_NOISE_LINE = re.compile(r"^[\s\W]{0,5}$")

# Arabic section-header OCR artifacts: "42 gals s81s641)...", "4 oxi ndessls..."
# These start with a verse/section number + space (NOT digit+period+space like real footnotes).
_SECTION_NOISE = re.compile(r"^\d+\s")

# Any 2+ consecutive ASCII letters — used to detect lines with no real alpha content.
_ALPHA_WORD = re.compile(r"[a-zA-Z]{2,}")


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_line(line: str) -> str:
    line = _ARABIC_BLOCK.sub("", line)
    line = re.sub(r"\s{2,}", " ", line)
    return line.strip()


def clean_block(text: str) -> str:
    """Clean and collapse a multi-line text block."""
    lines = [clean_line(ln) for ln in text.splitlines()]
    lines = [ln for ln in lines if not _NOISE_LINE.match(ln)]
    # Collapse runs of blank lines to a single blank
    result: list[str] = []
    prev_blank = False
    for ln in lines:
        if ln == "":
            if not prev_blank:
                result.append("")
            prev_blank = True
        else:
            result.append(ln)
            prev_blank = False
    # Strip trailing OCR garbage lines (Arabic section-header artifacts).
    # Conservative: only remove lines that are clearly noise:
    #   - no alphabetic content at all (pure symbols/digits), OR
    #   - start with digit+space (Arabic verse-number headers in OCR output;
    #     real footnotes use "digit. text", not "digit text")
    while result and result[-1]:
        last = result[-1]
        if _SECTION_NOISE.match(last) or not _ALPHA_WORD.search(last):
            result.pop()
        else:
            break
    return "\n".join(result).strip()


# ── Parsing ───────────────────────────────────────────────────────────────────

def split_into_surah_blocks(text: str) -> list[tuple[int, str, str, str]]:
    """
    Split the full text into (surah_number, name, english_name, body) tuples.
    The body is everything from the header line to the next surah header.
    """
    lines = text.splitlines()
    boundaries: list[tuple[int, int, str, str]] = []  # (line_idx, surah_num, name, eng)

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = _SURAH_HEADER.match(stripped) or _SURAH_HEADER_NO_PREFIX.match(stripped)
        if m:
            num = int(m.group(1))
            # Sanity check: skip the ToC entries (they appear before surah 1's body)
            # The real headers come after the ToC; we detect them by requiring
            # that surah numbers appear in order.
            if boundaries and num <= boundaries[-1][1]:
                continue
            boundaries.append((i, num, m.group(2).strip(), (m.group(3) or "").strip()))

    surah_blocks: list[tuple[int, str, str, str]] = []
    for idx, (line_idx, num, name, eng) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(lines)
        body = "\n".join(lines[line_idx + 1: end])
        surah_blocks.append((num, name, eng, body))

    return surah_blocks


def parse_surah_body(surah_num: int, body: str) -> tuple[str, list[dict]]:
    """
    Split a surah body into (introduction, verses).

    The introduction is everything before the first verse marker `({N}:{1})`.
    Verses are parsed with their footnote commentary.
    """
    lines = body.splitlines()

    # Find the first verse marker line
    first_verse_line = None
    for i, line in enumerate(lines):
        if _VERSE_MARKER.match(line.strip()):
            first_verse_line = i
            break

    if first_verse_line is None:
        # Entire body is introduction (some short surahs)
        intro = clean_block(body)
        return intro, []

    intro_raw = "\n".join(lines[:first_verse_line])
    verse_body = "\n".join(lines[first_verse_line:])
    intro = clean_block(intro_raw)
    verses = parse_verses(surah_num, verse_body)
    return intro, verses


def parse_verses(surah_num: int, text: str) -> list[dict]:
    """
    Parse verse markers and their associated footnotes from a surah's verse section.

    Each verse record gets:
        - ayah: int
        - verse_text: the translation Maududi provides inline with the marker
                      (may span multiple OCR-wrapped lines before the first footnote)
        - commentary: all footnote text that follows this verse marker up to the next
    """
    lines = text.splitlines()
    verses: list[dict] = []
    current: dict | None = None
    commentary_lines: list[str] = []
    in_verse_continuation = False  # True between verse marker and first footnote/blank

    def flush() -> None:
        if current is not None:
            current["commentary"] = clean_block("\n".join(commentary_lines))
            verses.append(current)
        commentary_lines.clear()

    for line in lines:
        stripped = clean_line(line)
        if not stripped:
            # A blank line ends verse-text continuation; subsequent lines are commentary
            if in_verse_continuation:
                in_verse_continuation = False
            elif commentary_lines:
                commentary_lines.append("")
            continue

        vm = _VERSE_MARKER.match(stripped)
        if vm and int(vm.group(1)) == surah_num:
            flush()
            current = {
                "surah": surah_num,
                "ayah": int(vm.group(2)),
                "verse_text": vm.group(3).strip(),
                "commentary": "",
            }
            commentary_lines = []
            in_verse_continuation = True
            continue

        if in_verse_continuation:
            if _FOOTNOTE_START.match(stripped):
                # First footnote signals end of verse translation
                in_verse_continuation = False
                commentary_lines.append(stripped)
            else:
                # Continuation of verse translation across OCR line-wrap
                current["verse_text"] = (current["verse_text"].rstrip() + " " + stripped).strip()
            continue

        if current is not None:
            commentary_lines.append(stripped)

    flush()
    return verses


def parse_all(text: str) -> list[dict]:
    """Parse the full raw text into a list of surah objects."""
    from tqdm import tqdm

    surah_blocks = split_into_surah_blocks(text)
    result: list[dict] = []

    for num, name, eng, body in tqdm(surah_blocks, desc="parsing", unit="surah"):
        intro, verses = parse_surah_body(num, body)
        result.append({
            "surah": num,
            "name": name,
            "english_name": eng,
            "introduction": intro,
            "verses": verses,
        })

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Maududi djvu text to JSON.")
    parser.add_argument(
        "--surah",
        type=int,
        default=None,
        help="Parse and print a single surah to stdout (for inspection).",
    )
    args = parser.parse_args()

    if not RAW_FILE.exists():
        print(f"ERROR: {RAW_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    text = RAW_FILE.read_text(encoding="utf-8")

    if args.surah:
        surah_blocks = split_into_surah_blocks(text)
        match = next((b for b in surah_blocks if b[0] == args.surah), None)
        if not match:
            print(f"Surah {args.surah} not found.", file=sys.stderr)
            sys.exit(1)
        num, name, eng, body = match
        intro, verses = parse_surah_body(num, body)
        print(json.dumps({
            "surah": num,
            "name": name,
            "english_name": eng,
            "introduction": intro,
            "verses": verses,
        }, indent=2, ensure_ascii=False))
        return

    data = parse_all(text)

    # Write full dataset
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    out_full = DIST_DIR / "maududi.json"
    out_full.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {out_full}  ({out_full.stat().st_size // 1024} KB)")

    # Write per-chapter files
    CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)
    for surah in data:
        out = CHAPTERS_DIR / f"{surah['surah']}.json"
        out.write_text(json.dumps(surah, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {CHAPTERS_DIR}/*.json  ({len(data)} files)")

    # Write chapter index
    index = [
        {
            "surah": s["surah"],
            "name": s["name"],
            "english_name": s["english_name"],
            "verse_count": len(s["verses"]),
        }
        for s in data
    ]
    out_index = CHAPTERS_DIR / "index.json"
    out_index.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written: {out_index}")

    # Print summary
    total_verses = sum(len(s["verses"]) for s in data)
    surahs_with_intro = sum(1 for s in data if s["introduction"])
    print(f"\nSummary: {len(data)} surahs, {total_verses} verse records, "
          f"{surahs_with_intro} with introductions")


if __name__ == "__main__":
    main()
