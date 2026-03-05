# maududi-json

Maududi's *Tafhim al-Quran* (Towards Understanding the Quran), translated by Zafar Ishaq Ansari (The Islamic Foundation), structured as JSON.

All 114 surahs — including surah introductions and per-verse commentary (tafsir) footnotes.

## CDN

Files are served via [jsDelivr](https://www.jsdelivr.com/) directly from this repository. Replace `@main` with a tagged release (e.g. `@1.0.0`) for a stable URL.

```
https://cdn.jsdelivr.net/gh/EfeKaralar/maududi-json@main/dist/maududi.json
https://cdn.jsdelivr.net/gh/EfeKaralar/maududi-json@main/dist/chapters/index.json
https://cdn.jsdelivr.net/gh/EfeKaralar/maududi-json@main/dist/chapters/{chapterNumber}.json
```

## Dataset

| File | Description |
|------|-------------|
| `dist/maududi.json` | Complete dataset — all 114 surahs in a single file (~8.8 MB) |
| `dist/chapters/index.json` | Lightweight index — surah number, name, English name, verse count |
| `dist/chapters/{N}.json` | One file per surah (1–114) |

## Schema

### Chapter index (`dist/chapters/index.json`)

```json
[
  {
    "surah": 1,
    "name": "Al Fatihah",
    "english_name": "The Opening",
    "verse_count": 7
  }
]
```

### Per-chapter (`dist/chapters/1.json`)

```json
{
  "surah": 1,
  "name": "Al Fatihah",
  "english_name": "The Opening",
  "introduction": "Al-Fatihah, which is the real beginning...",
  "verses": [
    {
      "surah": 1,
      "ayah": 1,
      "verse_text": "In the name of Allah, the Merciful, the Compassionate!",
      "commentary": "1. One of the many practices taught by Islam..."
    }
  ]
}
```

- `introduction` — Maududi's extended thematic introduction to the surah (present for all 114 surahs).
- `verse_text` — Ansari's English translation of the verse as rendered in the book.
- `commentary` — The footnote text attached to that verse. Empty string `""` if the verse has no footnote.

## Source

Parsed from the djvu OCR text of the complete English translation:

> Towards Understanding the Quran (Tafhim al-Quran), Sayyid Abul Ala Maududi.
> Translated by Zafar Ishaq Ansari. The Islamic Foundation.
> https://archive.org/details/towards-understanding-quran-maududi

## Regenerating

```bash
uv sync
uv run python scripts/parse.py           # regenerate dist/
uv run python scripts/parse.py --surah 2 # inspect a single surah
```

## License

The dataset structure and parsing scripts are MIT licensed.

The underlying text is © The Islamic Foundation (Zafar Ishaq Ansari translation).
This dataset is for research and non-commercial use only.
