# maududi-json

Structured JSON dataset parsed from Maududi's *Tafhim al-Quran* (Towards Understanding the Quran), translated by Zafar Ishaq Ansari (The Islamic Foundation).

## Source

Parsed from the djvu OCR text available at:
https://archive.org/details/towards-understanding-quran-maududi

## Dataset

`dist/maududi.json` — full dataset (all 114 surahs)
`dist/by_surah/{N}.json` — one file per surah

### Schema

```json
{
  "surah": 2,
  "name": "Al Baqarah",
  "english_name": "The Cow",
  "introduction": "...",
  "verses": [
    {
      "surah": 2,
      "ayah": 255,
      "verse_text": "Allah - there is no deity except Him...",
      "commentary": "..."
    }
  ]
}
```

## Usage

```bash
uv sync
uv run python scripts/parse.py           # regenerate dist/
uv run python scripts/parse.py --surah 1 # inspect a single surah
```

## License

The dataset structure and parsing scripts are MIT licensed.
The underlying text is © The Islamic Foundation (Zafar Ishaq Ansari translation).
This dataset is for research and non-commercial use only.
