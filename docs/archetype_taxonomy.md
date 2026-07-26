# Archetype taxonomy: MTGGoldfish vs Videre (MTGOFormatData)

Generated 2026-07-25 from the live `data-publish` snapshot (`latest/archetypes/*.json` and `latest/mtgo-decklists/*.json`).

The two deck sources name archetypes differently: MTGGoldfish pages drive the
archetype list, while MTGO decks are classified with the vendored MTGOFormatData
datasets. The publisher reconciles them with `_ArchetypeHrefResolver`
(`publisher/runner.py`) — curated alias, exact slug, dash-insensitive slug, then
unique token-subset — preferring the MTGGoldfish name whenever a match exists.
Curated aliases live in `publisher/archetype_aliases.py`.

**Caveats**

- Name mapping cannot fix *misclassification*: e.g. Videre/MTGOFormatData labels
  some Modern Boros Ponza decks as "Boros Energy". That is a defect in the
  vendored classification rules (`vendor/mtgo_format_data`), upstream of naming.
- Ambiguous Videre names (could fold into several MTGGoldfish archetypes) are
  deliberately left unmerged and publish as MTGO-only archetypes, e.g. Modern
  "Prowess" (Grixis/Izzet/Jeskai candidates), "Broodscale" (three color splits),
  Legacy "Energy" (Boros/Mardu), Standard "Reanimator" (4c/Dimir/Sultai).
- Deck counts are from the 7-day window in the snapshot.

## Legacy

MTGO decks in window: 288; merged into MTGGoldfish archetypes: 171 (59%); MTGO-only: 117.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| 8-Cast | — |
| Affinity Stompy | — |
| Aluren | Aluren (3) |
| Arclight Phoenix | — |
| Azorius Control | — |
| Azorius Stoneblade | Azorius Stoneblade (1) |
| Azorius Tempo | — |
| Beanstalk Control (Non-Yorion) | White Beanstalk (3) [alias] |
| Beseech Storm | — |
| Blue Artifacts | Blue Artifacts (20) |
| Blue Cloudpost | Post (1) [alias] |
| Boros Energy | — |
| Boros Initiative | — |
| Car Stompy | — |
| Cephalid Breakfast | Cephalid breakfast (3) |
| Cradle Control | Cradle Control (1) |
| Death and Taxes (60 Card) | Death & Taxes (10) [alias] |
| Death and Taxes (Yorion) - Black/White | — |
| Death and Taxes (Yorion) - Mono White | — |
| Death's Shadow | Dimir Death 's Shadow (3) [auto] |
| Dimir Car | — |
| Dimir Control | — |
| Dimir Tempo | Dimir Delver (1) [alias]; Dimir Tempo (47) |
| Doomsday | Doomsday (27) |
| Eldrazi | Eldrazi (2) |
| Esper Stoneblade | — |
| Esper Tempo | Esper Delver (1) [alias] |
| Goblins | — |
| Grixis Tempo | — |
| HullDay Echo Stompy | — |
| Izzet Delver | Izzet Delver (7) |
| Jeskai Control | — |
| Jund | — |
| Lands | Lands (7) |
| LED Dredge | Dredge (1) [auto] |
| Mardu Energy | — |
| Merfolk | — |
| Mono Black Midrange | Mono Black Midrange (4) |
| Mono Black Reanimator | — |
| Mono-Blue Tempo | Mono Blue Delver (3) [alias] |
| Mystic Forge Combo | Mystic Forge Combo (6) |
| Naya Initiative | — |
| Necrodominance Combo | — |
| Nic Fit | Sultai Nic Fit (1) [auto] |
| Ninjas | — |
| Ocelot Pride Tempo | — |
| Omni-Tell | — |
| Oops! All Spells | Oops ! All Spells (2) |
| Painter | Painter (1) |
| Rakdos Reanimator | — |
| Reanimator | Grixis Reanimator (7) [auto]; Jund Reanimator (2) [alias]; Mardu Reanimator (1) [auto]; Sultai Reanimator (3) [auto] |
| Red Stompy | — |
| Saga Storm | — |
| Selesnya Depths | — |
| Sneak and Show | — |
| Stiflenought | Stiflenought (1) |
| Sultai Depths | — |
| The EPIC Storm | TES (2) [alias] |
| Tron | — |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| Aluren | 3 | same name |
| Azorius Midrange | 16 | **MTGO-only** (union entry) |
| Azorius Stoneblade | 1 | same name |
| Blue Artifacts | 20 | same name |
| Cephalid breakfast | 3 | same name |
| Charbelcher | 1 | **MTGO-only** (union entry) |
| Cradle Control | 1 | same name |
| Creative combo | 1 | **MTGO-only** (union entry) |
| Death & Taxes | 10 | → Death and Taxes (60 Card) [alias] |
| Dimir Death 's Shadow | 3 | → Death's Shadow [auto] |
| Dimir Delver | 1 | → Dimir Tempo [alias] |
| Dimir Midrange | 23 | **MTGO-only** (union entry) |
| Dimir Tempo | 47 | same name |
| Doomsday | 27 | same name |
| Dredge | 1 | → LED Dredge [auto] |
| Eldrazi | 2 | same name |
| Elves | 1 | **MTGO-only** (union entry) |
| Energy | 21 | **MTGO-only** (union entry) |
| Esper Delver | 1 | → Esper Tempo [alias] |
| Esper Midrange | 6 | **MTGO-only** (union entry) |
| Golgari Landfall | 4 | **MTGO-only** (union entry) |
| Grixis Reanimator | 7 | → Reanimator [auto] |
| Gruul Stompy | 1 | **MTGO-only** (union entry) |
| Izzet Delver | 7 | same name |
| Izzet Midrange | 13 | **MTGO-only** (union entry) |
| Jeskai Midrange | 2 | **MTGO-only** (union entry) |
| Jeskai Stoneblade | 1 | **MTGO-only** (union entry) |
| Jund Reanimator | 2 | → Reanimator [alias] |
| Lands | 7 | same name |
| Mardu Reanimator | 1 | → Reanimator [auto] |
| Mono Black Midrange | 4 | same name |
| Mono Black Stompy | 2 | **MTGO-only** (union entry) |
| Mono Blue Delver | 3 | → Mono-Blue Tempo [alias] |
| Mystic Forge Combo | 6 | same name |
| Naya Stompy | 4 | **MTGO-only** (union entry) |
| Oops ! All Spells | 2 | same name |
| Painter | 1 | same name |
| Post | 1 | → Blue Cloudpost [alias] |
| Show and Tell | 13 | **MTGO-only** (union entry) |
| Stiflenought | 1 | same name |
| Sultai Nic Fit | 1 | → Nic Fit [auto] |
| Sultai Reanimator | 3 | → Reanimator [auto] |
| Temur Cascade Rhinos | 1 | **MTGO-only** (union entry) |
| TES | 2 | → The EPIC Storm [alias] |
| Unknown | 7 | unclassified (card pool only) |
| White Beanstalk | 3 | → Beanstalk Control (Non-Yorion) [alias] |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| 8-Cast | MTGGoldfish | — | 0 |
| Affinity Stompy | MTGGoldfish | — | 0 |
| Aluren | MTGGoldfish | Aluren | 3 |
| Arclight Phoenix | MTGGoldfish | — | 0 |
| Azorius Control | MTGGoldfish | — | 0 |
| Azorius Midrange | Videre (MTGO-only) | — | 16 |
| Azorius Stoneblade | MTGGoldfish | Azorius Stoneblade | 1 |
| Azorius Tempo | MTGGoldfish | — | 0 |
| Beanstalk Control (Non-Yorion) | MTGGoldfish | White Beanstalk | 3 |
| Beseech Storm | MTGGoldfish | — | 0 |
| Blue Artifacts | MTGGoldfish | Blue Artifacts | 20 |
| Blue Cloudpost | MTGGoldfish | Post | 1 |
| Boros Energy | MTGGoldfish | — | 0 |
| Boros Initiative | MTGGoldfish | — | 0 |
| Car Stompy | MTGGoldfish | — | 0 |
| Cephalid Breakfast | MTGGoldfish | Cephalid breakfast | 3 |
| Charbelcher | Videre (MTGO-only) | — | 1 |
| Cradle Control | MTGGoldfish | Cradle Control | 1 |
| Creative combo | Videre (MTGO-only) | — | 1 |
| Death and Taxes (60 Card) | MTGGoldfish | Death & Taxes | 10 |
| Death and Taxes (Yorion) - Black/White | MTGGoldfish | — | 0 |
| Death and Taxes (Yorion) - Mono White | MTGGoldfish | — | 0 |
| Death's Shadow | MTGGoldfish | Dimir Death 's Shadow | 3 |
| Dimir Car | MTGGoldfish | — | 0 |
| Dimir Control | MTGGoldfish | — | 0 |
| Dimir Midrange | Videre (MTGO-only) | — | 23 |
| Dimir Tempo | MTGGoldfish | Dimir Delver; Dimir Tempo | 48 |
| Doomsday | MTGGoldfish | Doomsday | 27 |
| Eldrazi | MTGGoldfish | Eldrazi | 2 |
| Elves | Videre (MTGO-only) | — | 1 |
| Energy | Videre (MTGO-only) | — | 21 |
| Esper Midrange | Videre (MTGO-only) | — | 6 |
| Esper Stoneblade | MTGGoldfish | — | 0 |
| Esper Tempo | MTGGoldfish | Esper Delver | 1 |
| Goblins | MTGGoldfish | — | 0 |
| Golgari Landfall | Videre (MTGO-only) | — | 4 |
| Grixis Tempo | MTGGoldfish | — | 0 |
| Gruul Stompy | Videre (MTGO-only) | — | 1 |
| HullDay Echo Stompy | MTGGoldfish | — | 0 |
| Izzet Delver | MTGGoldfish | Izzet Delver | 7 |
| Izzet Midrange | Videre (MTGO-only) | — | 13 |
| Jeskai Control | MTGGoldfish | — | 0 |
| Jeskai Midrange | Videre (MTGO-only) | — | 2 |
| Jeskai Stoneblade | Videre (MTGO-only) | — | 1 |
| Jund | MTGGoldfish | — | 0 |
| Lands | MTGGoldfish | Lands | 7 |
| LED Dredge | MTGGoldfish | Dredge | 1 |
| Mardu Energy | MTGGoldfish | — | 0 |
| Merfolk | MTGGoldfish | — | 0 |
| Mono Black Midrange | MTGGoldfish | Mono Black Midrange | 4 |
| Mono Black Reanimator | MTGGoldfish | — | 0 |
| Mono Black Stompy | Videre (MTGO-only) | — | 2 |
| Mono-Blue Tempo | MTGGoldfish | Mono Blue Delver | 3 |
| Mystic Forge Combo | MTGGoldfish | Mystic Forge Combo | 6 |
| Naya Initiative | MTGGoldfish | — | 0 |
| Naya Stompy | Videre (MTGO-only) | — | 4 |
| Necrodominance Combo | MTGGoldfish | — | 0 |
| Nic Fit | MTGGoldfish | Sultai Nic Fit | 1 |
| Ninjas | MTGGoldfish | — | 0 |
| Ocelot Pride Tempo | MTGGoldfish | — | 0 |
| Omni-Tell | MTGGoldfish | — | 0 |
| Oops! All Spells | MTGGoldfish | Oops ! All Spells | 2 |
| Painter | MTGGoldfish | Painter | 1 |
| Rakdos Reanimator | MTGGoldfish | — | 0 |
| Reanimator | MTGGoldfish | Grixis Reanimator; Jund Reanimator; Mardu Reanimator; Sultai Reanimator | 13 |
| Red Stompy | MTGGoldfish | — | 0 |
| Saga Storm | MTGGoldfish | — | 0 |
| Selesnya Depths | MTGGoldfish | — | 0 |
| Show and Tell | Videre (MTGO-only) | — | 13 |
| Sneak and Show | MTGGoldfish | — | 0 |
| Stiflenought | MTGGoldfish | Stiflenought | 1 |
| Sultai Depths | MTGGoldfish | — | 0 |
| Temur Cascade Rhinos | Videre (MTGO-only) | — | 1 |
| The EPIC Storm | MTGGoldfish | TES | 2 |
| Tron | MTGGoldfish | — | 0 |

## Modern

MTGO decks in window: 651; merged into MTGGoldfish archetypes: 473 (72%); MTGO-only: 178.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| 4c HollowOne | — |
| 5c Midrange | — |
| Affinity | Affinity (30) |
| Amulet Titan | Amulet Titan (21) |
| Azorius Control | Azorius Control (27) |
| Azorius Energy | — |
| Azorius GenericBlink | Azorius Blink (9) [alias] |
| Bant Control | — |
| Belcher | Blue Belcher (11) [auto] |
| Boros Burn | — |
| Boros Energy | Boros Energy (66) |
| Boros Ponza | — |
| Crashing Footfalls | — |
| Death's Shadow | — |
| Devoted Combo | Devoted Combo (6) |
| Dimir Midrange | — |
| Dimir Murktide | — |
| Domain Zoo | Domain Zoo (23) |
| Eldrazi | Aggro Eldrazi (2) [auto]; Black Eldrazi (1) [auto]; Breach Eldrazi (2) [auto] |
| Eldrazi Ramp | Ramp Eldrazi (52) [alias] |
| Eldrazi Tron | — |
| Esper Control | — |
| Esper GenericBlink | Esper Blink (11) [alias] |
| Esper Midrange | Esper Midrange (1) |
| Esper Murktide | — |
| Generic Ragavan | — |
| Goryo's Vengeance | Goryo Reanimator (52) [alias] |
| Grixis Control | Grixis Control (1) |
| Grixis Midrange | — |
| Grixis Prowess | — |
| Grixis Reanimator | Grixis Reanimator (15) |
| Gruul Basking Broodscale Combo | — |
| Hammer Time | — |
| Indomitable Creativity | 5 Color Creativity (1) [alias]; Jund Creativity (1) [alias] |
| Izzet Prowess | — |
| Izzet Steel-Cutter | Izzet Cutter (3) [auto] |
| IzzetControl | — |
| Jeskai Control | — |
| Jeskai Energy | Jeskai Energy (2) |
| Jeskai Prowess | — |
| Living End | Living End (21) |
| Mardu Energy | Mardu Energy (6) |
| Mardu HollowOne | — |
| Merfolk | Merfolk (1) |
| Mill | Mill (3) |
| Mono-Black Midrange | — |
| Mono-Green Basking Broodscale Combo | — |
| Mono-Green Eldrazi | — |
| Neobrand | Neobrand (30) |
| Rakdos Burn | — |
| Rakdos HollowOne | — |
| Ruby Storm | Ruby Storm (25) |
| Simic Basking Broodscale Combo | — |
| Song of Creation | Song Of Creation (2) |
| Sultai Midrange | — |
| The Rock | — |
| Through the Breach | — |
| Tron | Tron (40) |
| Yawgmoth | Yawgmoth (8) |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| 5 Color Creativity | 1 | → Indomitable Creativity [alias] |
| Abzan Blink | 1 | **MTGO-only** (union entry) |
| Affinity | 30 | same name |
| Aggro Eldrazi | 2 | → Eldrazi [auto] |
| Amulet Titan | 21 | same name |
| Azorius Blink | 9 | → Azorius GenericBlink [alias] |
| Azorius Control | 27 | same name |
| Black Eldrazi | 1 | → Eldrazi [auto] |
| Blue Belcher | 11 | → Belcher [auto] |
| Bogles | 1 | **MTGO-only** (union entry) |
| Boros Aggro | 16 | **MTGO-only** (union entry) |
| Boros Energy | 66 | same name |
| Boros Scam | 6 | **MTGO-only** (union entry) |
| Breach Eldrazi | 2 | → Eldrazi [auto] |
| Broodscale | 42 | **MTGO-only** (union entry) |
| Burn | 6 | **MTGO-only** (union entry) |
| Cosmo Fling | 8 | **MTGO-only** (union entry) |
| Devoted Combo | 6 | same name |
| Dimir Frog | 17 | **MTGO-only** (union entry) |
| Dimir Reanimator | 1 | **MTGO-only** (union entry) |
| Domain Zoo | 23 | same name |
| Esper Blink | 11 | → Esper GenericBlink [alias] |
| Esper Frog | 1 | **MTGO-only** (union entry) |
| Esper Midrange | 1 | same name |
| Esper Scam | 6 | **MTGO-only** (union entry) |
| Golgari Scam | 1 | **MTGO-only** (union entry) |
| Goryo Reanimator | 52 | → Goryo's Vengeance [alias] |
| Grixis Control | 1 | same name |
| Grixis Frog | 1 | **MTGO-only** (union entry) |
| Grixis Reanimator | 15 | same name |
| Grixis Saga | 1 | **MTGO-only** (union entry) |
| Hollow One | 6 | **MTGO-only** (union entry) |
| Izzet Cutter | 3 | → Izzet Steel-Cutter [auto] |
| Jeskai Energy | 2 | same name |
| Jund Burn | 6 | **MTGO-only** (union entry) |
| Jund Creativity | 1 | → Indomitable Creativity [alias] |
| Jund Midrange | 1 | **MTGO-only** (union entry) |
| Lantern | 1 | **MTGO-only** (union entry) |
| Living End | 21 | same name |
| Mardu Energy | 6 | same name |
| Merfolk | 1 | same name |
| Mill | 3 | same name |
| Mono Black Scam | 1 | **MTGO-only** (union entry) |
| Mono Blue Control | 2 | **MTGO-only** (union entry) |
| Necrodominance | 7 | **MTGO-only** (union entry) |
| Neobrand | 30 | same name |
| Orzhov Blink | 3 | **MTGO-only** (union entry) |
| Phoenix | 2 | **MTGO-only** (union entry) |
| Prowess | 22 | **MTGO-only** (union entry) |
| Rakdos Midrange | 1 | **MTGO-only** (union entry) |
| Ramp Eldrazi | 52 | → Eldrazi Ramp [alias] |
| Ruby Storm | 25 | same name |
| Samwise | 1 | **MTGO-only** (union entry) |
| Scapeshift | 2 | **MTGO-only** (union entry) |
| Simic Ritual | 6 | **MTGO-only** (union entry) |
| Song Of Creation | 2 | same name |
| Soultrader Combo | 1 | **MTGO-only** (union entry) |
| Sultai Scam | 1 | **MTGO-only** (union entry) |
| The Rack | 2 | **MTGO-only** (union entry) |
| Tron | 40 | same name |
| Unknown | 1 | unclassified (card pool only) |
| WBRG Energy | 1 | **MTGO-only** (union entry) |
| WUBG Blink | 1 | **MTGO-only** (union entry) |
| WUBR Control | 1 | **MTGO-only** (union entry) |
| WURG Control | 1 | **MTGO-only** (union entry) |
| Yawgmoth | 8 | same name |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| 4c HollowOne | MTGGoldfish | — | 0 |
| 5c Midrange | MTGGoldfish | — | 0 |
| Abzan Blink | Videre (MTGO-only) | — | 1 |
| Affinity | MTGGoldfish | Affinity | 30 |
| Amulet Titan | MTGGoldfish | Amulet Titan | 21 |
| Azorius Control | MTGGoldfish | Azorius Control | 27 |
| Azorius Energy | MTGGoldfish | — | 0 |
| Azorius GenericBlink | MTGGoldfish | Azorius Blink | 9 |
| Bant Control | MTGGoldfish | — | 0 |
| Belcher | MTGGoldfish | Blue Belcher | 11 |
| Bogles | Videre (MTGO-only) | — | 1 |
| Boros Aggro | Videre (MTGO-only) | — | 16 |
| Boros Burn | MTGGoldfish | — | 0 |
| Boros Energy | MTGGoldfish | Boros Energy | 66 |
| Boros Ponza | MTGGoldfish | — | 0 |
| Boros Scam | Videre (MTGO-only) | — | 6 |
| Broodscale | Videre (MTGO-only) | — | 42 |
| Burn | Videre (MTGO-only) | — | 6 |
| Cosmo Fling | Videre (MTGO-only) | — | 8 |
| Crashing Footfalls | MTGGoldfish | — | 0 |
| Death's Shadow | MTGGoldfish | — | 0 |
| Devoted Combo | MTGGoldfish | Devoted Combo | 6 |
| Dimir Frog | Videre (MTGO-only) | — | 17 |
| Dimir Midrange | MTGGoldfish | — | 0 |
| Dimir Murktide | MTGGoldfish | — | 0 |
| Dimir Reanimator | Videre (MTGO-only) | — | 1 |
| Domain Zoo | MTGGoldfish | Domain Zoo | 23 |
| Eldrazi | MTGGoldfish | Aggro Eldrazi; Black Eldrazi; Breach Eldrazi | 5 |
| Eldrazi Ramp | MTGGoldfish | Ramp Eldrazi | 52 |
| Eldrazi Tron | MTGGoldfish | — | 0 |
| Esper Control | MTGGoldfish | — | 0 |
| Esper Frog | Videre (MTGO-only) | — | 1 |
| Esper GenericBlink | MTGGoldfish | Esper Blink | 11 |
| Esper Midrange | MTGGoldfish | Esper Midrange | 1 |
| Esper Murktide | MTGGoldfish | — | 0 |
| Esper Scam | Videre (MTGO-only) | — | 6 |
| Generic Ragavan | MTGGoldfish | — | 0 |
| Golgari Scam | Videre (MTGO-only) | — | 1 |
| Goryo's Vengeance | MTGGoldfish | Goryo Reanimator | 52 |
| Grixis Control | MTGGoldfish | Grixis Control | 1 |
| Grixis Frog | Videre (MTGO-only) | — | 1 |
| Grixis Midrange | MTGGoldfish | — | 0 |
| Grixis Prowess | MTGGoldfish | — | 0 |
| Grixis Reanimator | MTGGoldfish | Grixis Reanimator | 15 |
| Grixis Saga | Videre (MTGO-only) | — | 1 |
| Gruul Basking Broodscale Combo | MTGGoldfish | — | 0 |
| Hammer Time | MTGGoldfish | — | 0 |
| Hollow One | Videre (MTGO-only) | — | 6 |
| Indomitable Creativity | MTGGoldfish | 5 Color Creativity; Jund Creativity | 2 |
| Izzet Prowess | MTGGoldfish | — | 0 |
| Izzet Steel-Cutter | MTGGoldfish | Izzet Cutter | 3 |
| IzzetControl | MTGGoldfish | — | 0 |
| Jeskai Control | MTGGoldfish | — | 0 |
| Jeskai Energy | MTGGoldfish | Jeskai Energy | 2 |
| Jeskai Prowess | MTGGoldfish | — | 0 |
| Jund Burn | Videre (MTGO-only) | — | 6 |
| Jund Midrange | Videre (MTGO-only) | — | 1 |
| Lantern | Videre (MTGO-only) | — | 1 |
| Living End | MTGGoldfish | Living End | 21 |
| Mardu Energy | MTGGoldfish | Mardu Energy | 6 |
| Mardu HollowOne | MTGGoldfish | — | 0 |
| Merfolk | MTGGoldfish | Merfolk | 1 |
| Mill | MTGGoldfish | Mill | 3 |
| Mono Black Scam | Videre (MTGO-only) | — | 1 |
| Mono Blue Control | Videre (MTGO-only) | — | 2 |
| Mono-Black Midrange | MTGGoldfish | — | 0 |
| Mono-Green Basking Broodscale Combo | MTGGoldfish | — | 0 |
| Mono-Green Eldrazi | MTGGoldfish | — | 0 |
| Necrodominance | Videre (MTGO-only) | — | 7 |
| Neobrand | MTGGoldfish | Neobrand | 30 |
| Orzhov Blink | Videre (MTGO-only) | — | 3 |
| Phoenix | Videre (MTGO-only) | — | 2 |
| Prowess | Videre (MTGO-only) | — | 22 |
| Rakdos Burn | MTGGoldfish | — | 0 |
| Rakdos HollowOne | MTGGoldfish | — | 0 |
| Rakdos Midrange | Videre (MTGO-only) | — | 1 |
| Ruby Storm | MTGGoldfish | Ruby Storm | 25 |
| Samwise | Videre (MTGO-only) | — | 1 |
| Scapeshift | Videre (MTGO-only) | — | 2 |
| Simic Basking Broodscale Combo | MTGGoldfish | — | 0 |
| Simic Ritual | Videre (MTGO-only) | — | 6 |
| Song of Creation | MTGGoldfish | Song Of Creation | 2 |
| Soultrader Combo | Videre (MTGO-only) | — | 1 |
| Sultai Midrange | MTGGoldfish | — | 0 |
| Sultai Scam | Videre (MTGO-only) | — | 1 |
| The Rack | Videre (MTGO-only) | — | 2 |
| The Rock | MTGGoldfish | — | 0 |
| Through the Breach | MTGGoldfish | — | 0 |
| Tron | MTGGoldfish | Tron | 40 |
| WBRG Energy | Videre (MTGO-only) | — | 1 |
| WUBG Blink | Videre (MTGO-only) | — | 1 |
| WUBR Control | Videre (MTGO-only) | — | 1 |
| WURG Control | Videre (MTGO-only) | — | 1 |
| Yawgmoth | MTGGoldfish | Yawgmoth | 8 |

## Pauper

MTGO decks in window: 341; merged into MTGGoldfish archetypes: 269 (78%); MTGO-only: 72.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| 4c Ephemerate | — |
| 5c Ephemerate | — |
| Azorius Faeries | — |
| Azorius Gates | Caw Gates (6) [alias] |
| Black Burn | — |
| Black Sacrifice | Mono Black Sacrifice (3) [auto] |
| Blue Terror | Mono Blue Terror (30) [alias] |
| Bogles | Aura Bogles (4) [auto] |
| Boros Bully | Boros Bully (2) |
| Boros Moxite | — |
| Boros Synthesizer | Boros Synthesizer (1) |
| Burn | Mono Red Burn (5) [auto] |
| Cycle Storm | Cycle Storm (3) |
| Devotion | — |
| Dimir Affinity | Dimir Affinity (3) |
| Dimir Control | — |
| Dimir Faeries | Dimir Faeries (14) |
| Dimir Terror | Dimir Terror (19) |
| Dredge | — |
| Elves | Elves (8) |
| Ephemerate Tron | Ephemerate Tron (4) |
| Esper Affinity | Esper Affinity (1) |
| Familiars | Azorius Familiars (4) [auto] |
| Food Gardens | — |
| Glintblade | — |
| Golgari Gardens | Golgari Garden (11) [alias] |
| Grixis Affinity | Grixis Affinity (8) |
| Grixis Control | — |
| Gruul Ponza | Gruul Ponza (16) |
| Gruul Ramp | Gruul Ramp (3) |
| Infect | — |
| Inside Out Combo | Tireless Tribe (1) [alias] |
| Izzet Affinity | — |
| Izzet Faeries | — |
| Izzet Terror | — |
| Jeskai Ephemerate | Jeskai Ephemerate (16) |
| Jund Gardens | — |
| Jund Wildfire | — |
| Mardu Synthesizer | — |
| Mono Red Madness | Red Madness (31) [auto] |
| Mono Red Pingers | — |
| Mono Red Rally | Red Rally (33) [auto] |
| Mono-Blue | — |
| Mono-Blue Delver | — |
| Mono-Blue Faeries | Mono Blue Faeries (4) |
| Mono-White Aggro | — |
| Mono-White Heroic | — |
| Poison Storm | — |
| Rakdos Madness | Rakdos Madness (3) |
| Ruby Storm | — |
| Selesnya Gates | — |
| Serpentine Curve | — |
| Slivers | — |
| Snacker Gates | — |
| Spy Combo | Spy Combo (7) |
| Sultai Faeries | — |
| Tron | Altar Tron (1) [auto]; Tron (15) |
| Turbo Fog | Turbo Fog (1) |
| Walls Combo | Walls (1) [auto]; Walls Cascade (1) [alias] |
| White Aggro | White Aggro (10) |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| Altar Tron | 1 | → Tron [auto] |
| Aura Bogles | 4 | → Bogles [auto] |
| Azorius Familiars | 4 | → Familiars [auto] |
| Boros Bully | 2 | same name |
| Boros Midrange | 2 | **MTGO-only** (union entry) |
| Boros Synthesizer | 1 | same name |
| Cat Altar | 1 | **MTGO-only** (union entry) |
| Caw Gates | 6 | → Azorius Gates [alias] |
| Cycle Storm | 3 | same name |
| Dimir Affinity | 3 | same name |
| Dimir Faeries | 14 | same name |
| Dimir Terror | 19 | same name |
| Elves | 8 | same name |
| Ephemerate Tron | 4 | same name |
| Esper Affinity | 1 | same name |
| Gates | 22 | **MTGO-only** (union entry) |
| Golgari Garden | 11 | → Golgari Gardens [alias] |
| Grixis Affinity | 8 | same name |
| Gruul Ponza | 16 | same name |
| Gruul Ramp | 3 | same name |
| Izzet Control | 1 | **MTGO-only** (union entry) |
| Jeskai Ephemerate | 16 | same name |
| Jund Graveyard | 1 | **MTGO-only** (union entry) |
| Jund Midrange | 28 | **MTGO-only** (union entry) |
| Mono Black Sacrifice | 3 | → Black Sacrifice [auto] |
| Mono Blue Faeries | 4 | same name |
| Mono Blue Terror | 30 | → Blue Terror [alias] |
| Mono Red Burn | 5 | → Burn [auto] |
| Orzhov Midrange | 5 | **MTGO-only** (union entry) |
| Rakdos Goblins | 1 | **MTGO-only** (union entry) |
| Rakdos Madness | 3 | same name |
| Red Madness | 31 | → Mono Red Madness [auto] |
| Red Rally | 33 | → Mono Red Rally [auto] |
| Spy Combo | 7 | same name |
| Tireless Tribe | 1 | → Inside Out Combo [alias] |
| Tron | 15 | same name |
| Turbo Fog | 1 | same name |
| Unknown | 11 | unclassified (card pool only) |
| Walls | 1 | → Walls Combo [auto] |
| Walls Cascade | 1 | → Walls Combo [alias] |
| White Aggro | 10 | same name |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| 4c Ephemerate | MTGGoldfish | — | 0 |
| 5c Ephemerate | MTGGoldfish | — | 0 |
| Azorius Faeries | MTGGoldfish | — | 0 |
| Azorius Gates | MTGGoldfish | Caw Gates | 6 |
| Black Burn | MTGGoldfish | — | 0 |
| Black Sacrifice | MTGGoldfish | Mono Black Sacrifice | 3 |
| Blue Terror | MTGGoldfish | Mono Blue Terror | 30 |
| Bogles | MTGGoldfish | Aura Bogles | 4 |
| Boros Bully | MTGGoldfish | Boros Bully | 2 |
| Boros Midrange | Videre (MTGO-only) | — | 2 |
| Boros Moxite | MTGGoldfish | — | 0 |
| Boros Synthesizer | MTGGoldfish | Boros Synthesizer | 1 |
| Burn | MTGGoldfish | Mono Red Burn | 5 |
| Cat Altar | Videre (MTGO-only) | — | 1 |
| Cycle Storm | MTGGoldfish | Cycle Storm | 3 |
| Devotion | MTGGoldfish | — | 0 |
| Dimir Affinity | MTGGoldfish | Dimir Affinity | 3 |
| Dimir Control | MTGGoldfish | — | 0 |
| Dimir Faeries | MTGGoldfish | Dimir Faeries | 14 |
| Dimir Terror | MTGGoldfish | Dimir Terror | 19 |
| Dredge | MTGGoldfish | — | 0 |
| Elves | MTGGoldfish | Elves | 8 |
| Ephemerate Tron | MTGGoldfish | Ephemerate Tron | 4 |
| Esper Affinity | MTGGoldfish | Esper Affinity | 1 |
| Familiars | MTGGoldfish | Azorius Familiars | 4 |
| Food Gardens | MTGGoldfish | — | 0 |
| Gates | Videre (MTGO-only) | — | 22 |
| Glintblade | MTGGoldfish | — | 0 |
| Golgari Gardens | MTGGoldfish | Golgari Garden | 11 |
| Grixis Affinity | MTGGoldfish | Grixis Affinity | 8 |
| Grixis Control | MTGGoldfish | — | 0 |
| Gruul Ponza | MTGGoldfish | Gruul Ponza | 16 |
| Gruul Ramp | MTGGoldfish | Gruul Ramp | 3 |
| Infect | MTGGoldfish | — | 0 |
| Inside Out Combo | MTGGoldfish | Tireless Tribe | 1 |
| Izzet Affinity | MTGGoldfish | — | 0 |
| Izzet Control | Videre (MTGO-only) | — | 1 |
| Izzet Faeries | MTGGoldfish | — | 0 |
| Izzet Terror | MTGGoldfish | — | 0 |
| Jeskai Ephemerate | MTGGoldfish | Jeskai Ephemerate | 16 |
| Jund Gardens | MTGGoldfish | — | 0 |
| Jund Graveyard | Videre (MTGO-only) | — | 1 |
| Jund Midrange | Videre (MTGO-only) | — | 28 |
| Jund Wildfire | MTGGoldfish | — | 0 |
| Mardu Synthesizer | MTGGoldfish | — | 0 |
| Mono Red Madness | MTGGoldfish | Red Madness | 31 |
| Mono Red Pingers | MTGGoldfish | — | 0 |
| Mono Red Rally | MTGGoldfish | Red Rally | 33 |
| Mono-Blue | MTGGoldfish | — | 0 |
| Mono-Blue Delver | MTGGoldfish | — | 0 |
| Mono-Blue Faeries | MTGGoldfish | Mono Blue Faeries | 4 |
| Mono-White Aggro | MTGGoldfish | — | 0 |
| Mono-White Heroic | MTGGoldfish | — | 0 |
| Orzhov Midrange | Videre (MTGO-only) | — | 5 |
| Poison Storm | MTGGoldfish | — | 0 |
| Rakdos Goblins | Videre (MTGO-only) | — | 1 |
| Rakdos Madness | MTGGoldfish | Rakdos Madness | 3 |
| Ruby Storm | MTGGoldfish | — | 0 |
| Selesnya Gates | MTGGoldfish | — | 0 |
| Serpentine Curve | MTGGoldfish | — | 0 |
| Slivers | MTGGoldfish | — | 0 |
| Snacker Gates | MTGGoldfish | — | 0 |
| Spy Combo | MTGGoldfish | Spy Combo | 7 |
| Sultai Faeries | MTGGoldfish | — | 0 |
| Tron | MTGGoldfish | Altar Tron; Tron | 16 |
| Turbo Fog | MTGGoldfish | Turbo Fog | 1 |
| Walls Combo | MTGGoldfish | Walls; Walls Cascade | 2 |
| White Aggro | MTGGoldfish | White Aggro | 10 |

## Pioneer

MTGO decks in window: 236; merged into MTGGoldfish archetypes: 106 (44%); MTGO-only: 130.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| 4c Legends | — |
| 4c Midrange | — |
| 4c Scapeshift | — |
| 5c Legends | — |
| 5c Scapeshift | — |
| Abzan Greasefang | Abzan Greasefang (18) |
| Atraxa Neoform | Sultai Neoform Combo (1) [alias] |
| Azorius Control | Azorius Control (7) |
| Bant Scapeshift | — |
| Boros Convoke | Boros Convoke (7) |
| Boros Hammer Time | — |
| Boros Heroic | — |
| Boros Token Control | — |
| Dimir Aggro | — |
| Dimir Discard | — |
| Dimir Midrange | — |
| Dimir Self-Bounce | Dimir Self Bounce (8) |
| Esper Control | — |
| Golgari Food | Golgari Food (1) |
| Golgari Insidious Roots | — |
| Golgari Midrange | Golgari Midrange (17) |
| Grixis Indomitable Creativity | — |
| Grixis Midrange | — |
| Grixis Transmogrify | — |
| Gruul Prowess | — |
| Hidden Strings | — |
| Izzet Aggro | — |
| Izzet Ensoul Artifact | — |
| Izzet Lessons | — |
| Izzet Midrange | — |
| Izzet Phoenix | Phoenix (7) [auto] |
| Izzet Prowess | — |
| Izzet Rona Combo | Rona Combo (2) [auto] |
| Jeskai Control | — |
| Jund Midrange | — |
| Jund Sacrifice | Jund Sacrifice (1) |
| Mardu Greasefang | — |
| Metalwork Colossus | — |
| Mono-Black Devotion | — |
| Mono-Black Discard | — |
| Mono-Black Midrange | Mono Black Midrange (3) |
| Mono-Green Toolbox | — |
| Mono-Red Prowess | — |
| Mono-White Humans | Mono White Humans (1) |
| Nykthos Ramp | Mono Green Devotion (2) [alias] |
| Orzhov Greasefang | Orzhov Greasefang (13) |
| Quintorius Combo | — |
| Rakdos Goblins | Rakdos Goblins (1) |
| Rakdos Midrange | — |
| Selesnya Angels | Selesnya Angels (3) |
| Selesnya Company | Selesnya Company (2) |
| Selesnya Counters | — |
| Selesnya Midrange | — |
| Simic Scapeshift | Simic Scapeshift (12) |
| Temur Prowess | — |
| Temur Scapeshift | — |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| 5 Color Gyruda | 3 | **MTGO-only** (union entry) |
| Abzan Greasefang | 18 | same name |
| Azorius Control | 7 | same name |
| Bant Stompy | 1 | **MTGO-only** (union entry) |
| Boros Convoke | 7 | same name |
| Dimir Ninjas | 11 | **MTGO-only** (union entry) |
| Dimir Self Bounce | 8 | same name |
| Golgari Food | 1 | same name |
| Golgari Midrange | 17 | same name |
| Golgari Stompy | 1 | **MTGO-only** (union entry) |
| Jund Sacrifice | 1 | same name |
| Mono Black Midrange | 3 | same name |
| Mono Green Devotion | 2 | → Nykthos Ramp [alias] |
| Mono Green Stompy | 2 | **MTGO-only** (union entry) |
| Mono Red Aggro | 68 | **MTGO-only** (union entry) |
| Mono White Humans | 1 | same name |
| Orzhov Greasefang | 13 | same name |
| Phoenix | 7 | → Izzet Phoenix [auto] |
| Rakdos Goblins | 1 | same name |
| Rona Combo | 2 | → Izzet Rona Combo [auto] |
| Selesnya Angels | 3 | same name |
| Selesnya Company | 2 | same name |
| Selesnya Elemental | 2 | **MTGO-only** (union entry) |
| Selesnya Stompy | 2 | **MTGO-only** (union entry) |
| Simic Scapeshift | 12 | same name |
| Simic Tempo | 4 | **MTGO-only** (union entry) |
| Sultai Neoform Combo | 1 | → Atraxa Neoform [alias] |
| Unknown | 36 | unclassified (card pool only) |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| 4c Legends | MTGGoldfish | — | 0 |
| 4c Midrange | MTGGoldfish | — | 0 |
| 4c Scapeshift | MTGGoldfish | — | 0 |
| 5 Color Gyruda | Videre (MTGO-only) | — | 3 |
| 5c Legends | MTGGoldfish | — | 0 |
| 5c Scapeshift | MTGGoldfish | — | 0 |
| Abzan Greasefang | MTGGoldfish | Abzan Greasefang | 18 |
| Atraxa Neoform | MTGGoldfish | Sultai Neoform Combo | 1 |
| Azorius Control | MTGGoldfish | Azorius Control | 7 |
| Bant Scapeshift | MTGGoldfish | — | 0 |
| Bant Stompy | Videre (MTGO-only) | — | 1 |
| Boros Convoke | MTGGoldfish | Boros Convoke | 7 |
| Boros Hammer Time | MTGGoldfish | — | 0 |
| Boros Heroic | MTGGoldfish | — | 0 |
| Boros Token Control | MTGGoldfish | — | 0 |
| Dimir Aggro | MTGGoldfish | — | 0 |
| Dimir Discard | MTGGoldfish | — | 0 |
| Dimir Midrange | MTGGoldfish | — | 0 |
| Dimir Ninjas | Videre (MTGO-only) | — | 11 |
| Dimir Self-Bounce | MTGGoldfish | Dimir Self Bounce | 8 |
| Esper Control | MTGGoldfish | — | 0 |
| Golgari Food | MTGGoldfish | Golgari Food | 1 |
| Golgari Insidious Roots | MTGGoldfish | — | 0 |
| Golgari Midrange | MTGGoldfish | Golgari Midrange | 17 |
| Golgari Stompy | Videre (MTGO-only) | — | 1 |
| Grixis Indomitable Creativity | MTGGoldfish | — | 0 |
| Grixis Midrange | MTGGoldfish | — | 0 |
| Grixis Transmogrify | MTGGoldfish | — | 0 |
| Gruul Prowess | MTGGoldfish | — | 0 |
| Hidden Strings | MTGGoldfish | — | 0 |
| Izzet Aggro | MTGGoldfish | — | 0 |
| Izzet Ensoul Artifact | MTGGoldfish | — | 0 |
| Izzet Lessons | MTGGoldfish | — | 0 |
| Izzet Midrange | MTGGoldfish | — | 0 |
| Izzet Phoenix | MTGGoldfish | Phoenix | 7 |
| Izzet Prowess | MTGGoldfish | — | 0 |
| Izzet Rona Combo | MTGGoldfish | Rona Combo | 2 |
| Jeskai Control | MTGGoldfish | — | 0 |
| Jund Midrange | MTGGoldfish | — | 0 |
| Jund Sacrifice | MTGGoldfish | Jund Sacrifice | 1 |
| Mardu Greasefang | MTGGoldfish | — | 0 |
| Metalwork Colossus | MTGGoldfish | — | 0 |
| Mono Green Stompy | Videre (MTGO-only) | — | 2 |
| Mono Red Aggro | Videre (MTGO-only) | — | 68 |
| Mono-Black Devotion | MTGGoldfish | — | 0 |
| Mono-Black Discard | MTGGoldfish | — | 0 |
| Mono-Black Midrange | MTGGoldfish | Mono Black Midrange | 3 |
| Mono-Green Toolbox | MTGGoldfish | — | 0 |
| Mono-Red Prowess | MTGGoldfish | — | 0 |
| Mono-White Humans | MTGGoldfish | Mono White Humans | 1 |
| Nykthos Ramp | MTGGoldfish | Mono Green Devotion | 2 |
| Orzhov Greasefang | MTGGoldfish | Orzhov Greasefang | 13 |
| Quintorius Combo | MTGGoldfish | — | 0 |
| Rakdos Goblins | MTGGoldfish | Rakdos Goblins | 1 |
| Rakdos Midrange | MTGGoldfish | — | 0 |
| Selesnya Angels | MTGGoldfish | Selesnya Angels | 3 |
| Selesnya Company | MTGGoldfish | Selesnya Company | 2 |
| Selesnya Counters | MTGGoldfish | — | 0 |
| Selesnya Elemental | Videre (MTGO-only) | — | 2 |
| Selesnya Midrange | MTGGoldfish | — | 0 |
| Selesnya Stompy | Videre (MTGO-only) | — | 2 |
| Simic Scapeshift | MTGGoldfish | Simic Scapeshift | 12 |
| Simic Tempo | Videre (MTGO-only) | — | 4 |
| Temur Prowess | MTGGoldfish | — | 0 |
| Temur Scapeshift | MTGGoldfish | — | 0 |

## Standard

MTGO decks in window: 348; merged into MTGGoldfish archetypes: 143 (41%); MTGO-only: 205.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| 4c Aggro | — |
| 4c Control | — |
| 4c Gearhulk | — |
| 4c Kona | — |
| 4c Legends | — |
| 4c Lessons | — |
| 4c Reanimator | — |
| 5c Control | — |
| 5c Elementals | — |
| 5c Legends | — |
| 5c Ramp | — |
| Abzan Midrange | — |
| Allies | — |
| Azorius Control | Azorius Control (2) |
| Azorius Momo | — |
| Azorius Tempo | — |
| Bant Airbending Combo | — |
| Boros Burn | Boros Burn (2) |
| Boros Control | — |
| Boros Manufacturing | — |
| Boros Tokens | — |
| Dimir Excruciator | — |
| Dimir Midrange | — |
| Dimir Reanimator | — |
| Esper Self-Bounce | Esper Self Bounce (1) |
| Golgari Insidious Roots | — |
| Golgari Midrange | — |
| Gruul Delirium | Gruul Delirium (1) |
| Gruul Midrange | — |
| Izzet Aggro | Izzet Aggro (4) |
| Izzet Lessons | Izzet Lessons (6) |
| Izzet Maestro | — |
| Izzet Prowess | — |
| Izzet Self-Bounce | — |
| Izzet Spellementals | Izzet Elementals (41) [alias] |
| Izzet Spells | — |
| Jeskai Artifacts | — |
| Jeskai Control | Jeskai Control (76) |
| Jeskai Elementals | — |
| Jeskai Lessons | — |
| Jeskai Manufacturing | — |
| Jeskai Oculus | — |
| Jund Delirium | — |
| Lifegain | — |
| Mardu Discard | — |
| Mono-Black Midrange | — |
| Mono-Green Landfall | — |
| Mono-Green Squirrels | — |
| Mono-Red Aggro | Mono Red Aggro (2) |
| Mono-Red Burn | — |
| Naya Delirium | Naya Delirium (4) |
| Naya Yuna | Naya Yuna (1) |
| Orzhov Control | — |
| Selesnya Gearhulk | — |
| Selesnya Landfall | — |
| Selesnya Ouroboroid | — |
| Selesnya Rabbits | — |
| Simic Ouroboroid | — |
| Sultai Control | Sultai Control (3) |
| Sultai Reanimator | — |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| Azorius Aggro | 1 | **MTGO-only** (union entry) |
| Azorius Artifacts | 2 | **MTGO-only** (union entry) |
| Azorius Control | 2 | same name |
| Azorius Midrange | 6 | **MTGO-only** (union entry) |
| Bant Cub | 1 | **MTGO-only** (union entry) |
| Bant Midrange | 3 | **MTGO-only** (union entry) |
| Boros Burn | 2 | same name |
| Dimir Control | 24 | **MTGO-only** (union entry) |
| Esper Self Bounce | 1 | same name |
| Gruul Delirium | 1 | same name |
| Izzet Aggro | 4 | same name |
| Izzet Elementals | 41 | → Izzet Spellementals [alias] |
| Izzet Lessons | 6 | same name |
| Izzet Midrange | 48 | **MTGO-only** (union entry) |
| Jeskai Control | 76 | same name |
| Landfall | 21 | **MTGO-only** (union entry) |
| Mardu Blade | 5 | **MTGO-only** (union entry) |
| Mono Red Aggro | 2 | same name |
| Mono White Control | 1 | **MTGO-only** (union entry) |
| Naya Delirium | 4 | same name |
| Naya Yuna | 1 | same name |
| Reanimator | 9 | **MTGO-only** (union entry) |
| Selesnya Cub | 69 | **MTGO-only** (union entry) |
| Sultai Control | 3 | same name |
| Temur Lessons | 7 | **MTGO-only** (union entry) |
| Temur Omniscience | 3 | **MTGO-only** (union entry) |
| Unknown | 5 | unclassified (card pool only) |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| 4c Aggro | MTGGoldfish | — | 0 |
| 4c Control | MTGGoldfish | — | 0 |
| 4c Gearhulk | MTGGoldfish | — | 0 |
| 4c Kona | MTGGoldfish | — | 0 |
| 4c Legends | MTGGoldfish | — | 0 |
| 4c Lessons | MTGGoldfish | — | 0 |
| 4c Reanimator | MTGGoldfish | — | 0 |
| 5c Control | MTGGoldfish | — | 0 |
| 5c Elementals | MTGGoldfish | — | 0 |
| 5c Legends | MTGGoldfish | — | 0 |
| 5c Ramp | MTGGoldfish | — | 0 |
| Abzan Midrange | MTGGoldfish | — | 0 |
| Allies | MTGGoldfish | — | 0 |
| Azorius Aggro | Videre (MTGO-only) | — | 1 |
| Azorius Artifacts | Videre (MTGO-only) | — | 2 |
| Azorius Control | MTGGoldfish | Azorius Control | 2 |
| Azorius Midrange | Videre (MTGO-only) | — | 6 |
| Azorius Momo | MTGGoldfish | — | 0 |
| Azorius Tempo | MTGGoldfish | — | 0 |
| Bant Airbending Combo | MTGGoldfish | — | 0 |
| Bant Cub | Videre (MTGO-only) | — | 1 |
| Bant Midrange | Videre (MTGO-only) | — | 3 |
| Boros Burn | MTGGoldfish | Boros Burn | 2 |
| Boros Control | MTGGoldfish | — | 0 |
| Boros Manufacturing | MTGGoldfish | — | 0 |
| Boros Tokens | MTGGoldfish | — | 0 |
| Dimir Control | Videre (MTGO-only) | — | 24 |
| Dimir Excruciator | MTGGoldfish | — | 0 |
| Dimir Midrange | MTGGoldfish | — | 0 |
| Dimir Reanimator | MTGGoldfish | — | 0 |
| Esper Self-Bounce | MTGGoldfish | Esper Self Bounce | 1 |
| Golgari Insidious Roots | MTGGoldfish | — | 0 |
| Golgari Midrange | MTGGoldfish | — | 0 |
| Gruul Delirium | MTGGoldfish | Gruul Delirium | 1 |
| Gruul Midrange | MTGGoldfish | — | 0 |
| Izzet Aggro | MTGGoldfish | Izzet Aggro | 4 |
| Izzet Lessons | MTGGoldfish | Izzet Lessons | 6 |
| Izzet Maestro | MTGGoldfish | — | 0 |
| Izzet Midrange | Videre (MTGO-only) | — | 48 |
| Izzet Prowess | MTGGoldfish | — | 0 |
| Izzet Self-Bounce | MTGGoldfish | — | 0 |
| Izzet Spellementals | MTGGoldfish | Izzet Elementals | 41 |
| Izzet Spells | MTGGoldfish | — | 0 |
| Jeskai Artifacts | MTGGoldfish | — | 0 |
| Jeskai Control | MTGGoldfish | Jeskai Control | 76 |
| Jeskai Elementals | MTGGoldfish | — | 0 |
| Jeskai Lessons | MTGGoldfish | — | 0 |
| Jeskai Manufacturing | MTGGoldfish | — | 0 |
| Jeskai Oculus | MTGGoldfish | — | 0 |
| Jund Delirium | MTGGoldfish | — | 0 |
| Landfall | Videre (MTGO-only) | — | 21 |
| Lifegain | MTGGoldfish | — | 0 |
| Mardu Blade | Videre (MTGO-only) | — | 5 |
| Mardu Discard | MTGGoldfish | — | 0 |
| Mono White Control | Videre (MTGO-only) | — | 1 |
| Mono-Black Midrange | MTGGoldfish | — | 0 |
| Mono-Green Landfall | MTGGoldfish | — | 0 |
| Mono-Green Squirrels | MTGGoldfish | — | 0 |
| Mono-Red Aggro | MTGGoldfish | Mono Red Aggro | 2 |
| Mono-Red Burn | MTGGoldfish | — | 0 |
| Naya Delirium | MTGGoldfish | Naya Delirium | 4 |
| Naya Yuna | MTGGoldfish | Naya Yuna | 1 |
| Orzhov Control | MTGGoldfish | — | 0 |
| Reanimator | Videre (MTGO-only) | — | 9 |
| Selesnya Cub | Videre (MTGO-only) | — | 69 |
| Selesnya Gearhulk | MTGGoldfish | — | 0 |
| Selesnya Landfall | MTGGoldfish | — | 0 |
| Selesnya Ouroboroid | MTGGoldfish | — | 0 |
| Selesnya Rabbits | MTGGoldfish | — | 0 |
| Simic Ouroboroid | MTGGoldfish | — | 0 |
| Sultai Control | MTGGoldfish | Sultai Control | 3 |
| Sultai Reanimator | MTGGoldfish | — | 0 |
| Temur Lessons | Videre (MTGO-only) | — | 7 |
| Temur Omniscience | Videre (MTGO-only) | — | 3 |

## Vintage

MTGO decks in window: 138; merged into MTGGoldfish archetypes: 128 (92%); MTGO-only: 10.

### MTGGoldfish archetypes

| Archetype | Videre decks folded in |
|---|---|
| Blue Tinker | Tinker (5) [auto] |
| Counter Vine | Countervine (8) [auto] |
| Dimir Lurrus Control | UB Lurrus Control (4) [alias] |
| Dimir Psychic Frog | — |
| Doomsday | Doomsday (4); Lurrus Doomsday (4) [auto] |
| Dredge | Dredge (3) |
| Eldrazi | — |
| Esper Lurrus Control | — |
| Esper Psychic Frog | — |
| Goblins | — |
| Grixis Lurrus Control | — |
| Hogaak Vine | — |
| Jewel Shops | Jewel Shops (4) |
| Lurrus Breach | Lurrus Breach (8) |
| Lurrus DRS | Lurrus DRS (6) |
| Lurrus PO | Lurrus PO (6) |
| Merfolk | — |
| Mono-White Aggro | — |
| Mono-White Initiative | Initiative (20) [auto] |
| Oath of Druids | Oath (7) [auto] |
| Oops! All Spells | — |
| Other Shops | Other Shops (2) |
| Painter | — |
| Paradoxical Outcome | PO (7) [alias] |
| Raker Shops | Raker Shops (33) |
| Scam | — |
| Sphere Shops | Sphere Shops (6) |
| Stiflenought | — |
| Sultai Midrange | — |
| Underworld Breach | Breach (1) [alias] |

### Videre archetypes observed

| Videre name | Decks | Resolution |
|---|---|---|
| Blue Control | 7 | **MTGO-only** (union entry) |
| Breach | 1 | → Underworld Breach [alias] |
| Countervine | 8 | → Counter Vine [auto] |
| Doomsday | 4 | same name |
| Dredge | 3 | same name |
| Initiative | 20 | → Mono-White Initiative [auto] |
| Jewel Shops | 4 | same name |
| Lurrus Breach | 8 | same name |
| Lurrus Doomsday | 4 | → Doomsday [auto] |
| Lurrus DRS | 6 | same name |
| Lurrus PO | 6 | same name |
| Oath | 7 | → Oath of Druids [auto] |
| Other Aggro | 1 | **MTGO-only** (union entry) |
| Other Lurrus | 2 | **MTGO-only** (union entry) |
| Other Shops | 2 | same name |
| PO | 7 | → Paradoxical Outcome [alias] |
| Raker Shops | 33 | same name |
| Sphere Shops | 6 | same name |
| Tinker | 5 | → Blue Tinker [auto] |
| UB Lurrus Control | 4 | → Dimir Lurrus Control [alias] |

### Condensed taxonomy

| Canonical archetype | Source | Videre labels folded in | MTGO decks |
|---|---|---|---|
| Blue Control | Videre (MTGO-only) | — | 7 |
| Blue Tinker | MTGGoldfish | Tinker | 5 |
| Counter Vine | MTGGoldfish | Countervine | 8 |
| Dimir Lurrus Control | MTGGoldfish | UB Lurrus Control | 4 |
| Dimir Psychic Frog | MTGGoldfish | — | 0 |
| Doomsday | MTGGoldfish | Doomsday; Lurrus Doomsday | 8 |
| Dredge | MTGGoldfish | Dredge | 3 |
| Eldrazi | MTGGoldfish | — | 0 |
| Esper Lurrus Control | MTGGoldfish | — | 0 |
| Esper Psychic Frog | MTGGoldfish | — | 0 |
| Goblins | MTGGoldfish | — | 0 |
| Grixis Lurrus Control | MTGGoldfish | — | 0 |
| Hogaak Vine | MTGGoldfish | — | 0 |
| Jewel Shops | MTGGoldfish | Jewel Shops | 4 |
| Lurrus Breach | MTGGoldfish | Lurrus Breach | 8 |
| Lurrus DRS | MTGGoldfish | Lurrus DRS | 6 |
| Lurrus PO | MTGGoldfish | Lurrus PO | 6 |
| Merfolk | MTGGoldfish | — | 0 |
| Mono-White Aggro | MTGGoldfish | — | 0 |
| Mono-White Initiative | MTGGoldfish | Initiative | 20 |
| Oath of Druids | MTGGoldfish | Oath | 7 |
| Oops! All Spells | MTGGoldfish | — | 0 |
| Other Aggro | Videre (MTGO-only) | — | 1 |
| Other Lurrus | Videre (MTGO-only) | — | 2 |
| Other Shops | MTGGoldfish | Other Shops | 2 |
| Painter | MTGGoldfish | — | 0 |
| Paradoxical Outcome | MTGGoldfish | PO | 7 |
| Raker Shops | MTGGoldfish | Raker Shops | 33 |
| Scam | MTGGoldfish | — | 0 |
| Sphere Shops | MTGGoldfish | Sphere Shops | 6 |
| Stiflenought | MTGGoldfish | — | 0 |
| Sultai Midrange | MTGGoldfish | — | 0 |
| Underworld Breach | MTGGoldfish | Breach | 1 |

## Totals

Across all six formats: 1290/2002 MTGO decks (64%) merge into a MTGGoldfish archetype; the remainder publish as MTGO-only union archetypes, so every deck stays reachable in the app.
