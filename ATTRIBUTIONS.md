# Attributions

This project incorporates ideas, techniques, and data from various open-source
projects and community resources. We gratefully acknowledge the following:

---

## Vendored Data and Adapted Code

### Badaro/MTGOFormatData

**Repository:** https://github.com/Badaro/MTGOFormatData

**Author:** Badaro

**License:** None published (no `LICENSE` file in the upstream repo). The
vendored content is factual archetype definitions and card color data for a
third-party game, refreshed via `scripts/update_vendor_data.py`.

**What we use:**
- Archetype definition files vendored under `vendor/mtgo_format_data/`
- `card_colors.json` for card color identity lookups

**Files influenced:**
- `utils/archetype_classifier.py` - Consumes the vendored datasets
- `scripts/update_vendor_data.py` - Refreshes the vendored copies

### Badaro/MTGOArchetypeParser

**Repository:** https://github.com/Badaro/MTGOArchetypeParser

**Author:** Badaro

**License:** MIT

**What we use:**
- The archetype rules format and matching semantics that
  `utils/archetype_classifier.py` reimplements in Python

**Credit:**
Badaro's MTGOFormatData and MTGOArchetypeParser projects are the community
standard for MTGO archetype classification. This repo's classifier is a
Python reimplementation of that rules engine over the vendored datasets.

---

## Data Sources

### Videre Project API

**Website:** https://api.videreproject.com

**Repository:** https://github.com/videre-project (api-services, MTGOBot)

**Author:** Videre Project

**License:** Apache-2.0 (their client and server code); the API itself is a
free community service with no published data-usage terms

**What we use:**
- MTGO event index, decklists, and standings served by their public REST
  API. The underlying decklist coverage is what mtgo.com publishes (Top 32
  of scheduled events plus the curated league 5-0 selection Daybreak
  Games releases), collected by their MTGOBot.

**Files influenced:**
- `navigators/videre.py` - Videre API client
- `services/mtgo_background_service.py` - MTGO event fetch window
- `publisher/runner.py` - MTGO decklist snapshot publishing

**Credit:**
The Videre Project maintains the community's most complete open MTGO
dataset and serves it for free. This repo previously scraped mtgo.com
directly; their API replaced that scraper entirely. Please support them at
https://github.com/videre-project.

---

## Libraries and Dependencies

### Python Libraries

- **msgspec** - Fast JSON serialization
- **loguru** - Logging
- **curl-cffi** - HTTP client for the Videre API

---

## AI Assistance

This project was developed with assistance from **Claude** (Anthropic), an AI
assistant that helped with:
- Code review and debugging
- Architecture decisions
- Documentation writing
- Best practices recommendations

---

## License Compatibility

This project is released under the MIT License (see `LICENSE`). We have
ensured compatibility with all dependencies:

- **MTGOArchetypeParser**: MIT License ✅ Compatible
- **MTGOFormatData**: No published license — vendored content is factual
  game data; flagged upstream for clarification
- **Videre Project**: Apache-2.0 code ✅ Compatible; we consume their public
  API as a data source and do not redistribute their code
- **Python libraries**: OSI-approved permissive licenses ✅ Compatible

---

## How to Contribute Attributions

If you believe we have:
1. Used your work without proper attribution
2. Misrepresented the extent of code reuse
3. Violated any license terms

Please open an issue at
https://github.com/Pedrogush/MTGO_Tools_Data/issues and we will
address it promptly.

---

## Disclaimer

This project is **not affiliated with or endorsed by:**
- Wizards of the Coast
- Hasbro
- Daybreak Games
- Any of the attributed projects above

Magic: The Gathering and MTGO are trademarks of Wizards of the Coast LLC.

This is a fan-made tool for personal use and metagame research. We respect all
intellectual property rights and terms of service.

---

**Last Updated:** 2026-07-24

**Maintained By:** Pedro (https://github.com/Pedrogush)

If you notice any attributions are missing or incorrect, please let us know!
