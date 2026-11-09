# Attributions

This project incorporates ideas, techniques, and data from various open-source
projects and community resources. We gratefully acknowledge the following:

---

## Data Sources

### Videre Project API

**Website:** https://api.videreproject.com

**Repository:** https://github.com/videre-project (api-services, MTGOBot)

**Author:** Videre Project

**License:** Apache-2.0 (their client and server code); the API itself is a
free community service with no published data-usage terms

**What we use:**
- MTGO event index, decklists, standings, and archetype classifications
  served by their public REST API. The underlying decklist coverage is what
  mtgo.com publishes (Top 32 of scheduled events plus the curated league 5-0
  selection Daybreak Games releases), collected by their MTGOBot. Their
  archetype labels follow Badaro's MTGOFormatData taxonomy
  (https://github.com/Badaro/MTGOFormatData), which this repo used to vendor
  and re-derive locally before taking the API's labels directly.

**Files influenced:**
- `navigators/videre.py` - Videre API client
- `navigators/videre_contract.py` - the API fields the client depends on
- `services/mtgo_background_service.py` - MTGO event fetch window
- `publisher/runner.py` - MTGO decklist snapshot publishing
- `publisher/mtgo_archive.py` - every other published product, derived from
  the MTGO decklist snapshot

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

- **MTGOFormatData / MTGOArchetypeParser**: no longer vendored or
  reimplemented — archetype labels now reach us as Videre API output
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

**Last Updated:** 2026-11-09

**Maintained By:** Pedro (https://github.com/Pedrogush)

If you notice any attributions are missing or incorrect, please let us know!
