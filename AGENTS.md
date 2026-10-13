# AGENTS.md

Notes for AI agents and contributors working on this repo. Keep this file
current: update it whenever a decision, convention or process below changes.

## What this is

A Home Assistant custom integration (domain `sarawak_energy_tariffs`),
distributed through HACS. It counts billing-period kWh from a user-chosen
cumulative energy sensor and prices that usage with Sarawak Energy's domestic
tariff (Tariff D). It's a community project, not affiliated with Sarawak Energy.

- Repo: https://github.com/Atsukio/ha-sarawak-energy-tariffs (public, MIT, owner `@Atsukio`)
- Minimum Home Assistant: 2024.11 (`hacs.json`). The local `brand/` icon only
  shows on 2026.3+.
- No external Python requirements.

## Layout

| Path | Purpose |
| --- | --- |
| `custom_components/sarawak_energy_tariffs/tariff.py` | Pure tariff maths and default tiers. **No Home Assistant imports**, so the tests can run without HA |
| `.../tracker.py` | `UsageTracker`: follows the source sensor, accumulates kWh, handles billing-day rollover, persists state with `Store` |
| `.../sensor.py` | Four sensors: billing period usage, estimated bill, current rate, current tier |
| `.../config_flow.py` | Setup and options flows; both share `_schema` / `_validate` / `_normalise` |
| `.../__init__.py` | Entry setup; `entry.runtime_data` holds the tracker; options changes reload the entry |
| `.../strings.json` | UI text. **`translations/en.json` must be an identical copy**; update both |
| `.../brand/` | `icon.png` (256px) and `icon@2x.png` (512px); generated, do not hand-edit |
| `scripts/make_icon.py` | Regenerates the icons (needs Pillow) |
| `tests/test_tariff.py` | Unit tests for `tariff.py`; plain `unittest`, loads the module by file path |
| `.github/workflows/validate.yml` | CI: HACS action, hassfest, unit tests |

## Tariff facts and decisions

- Default tiers come from https://www.sarawakenergy.com/customers/tariffs,
  checked 2026-10-14: 0-150 kWh 18 sen, 151-200 22, 201-300 25, 301-400 27,
  401-500 29.5, 501-700 30, 701-800 30.5, 801-1300 31, above 1300 31.5;
  minimum monthly charge RM 5.00.
- The page lists both "1 to 100" and "1 to 150" units at 18 sen. They're
  merged into one 0-150 band.
- The page doesn't say whether bands apply flat (one rate for all units, set
  by the band the total falls in) or as blocks (each rate only for units inside
  its band). Both are supported. **Flat is the default**, because the page's
  "For 1 to N units per month" wording suggests it. This has not been
  confirmed against a real bill.
- Tiers are stored as text, one `upper_kWh:RM_per_kWh` per line, ending with
  `inf:rate`. Commas also work as separators.
- If the tariff changes, update `DEFAULT_TIERS` in `tariff.py`, the table in
  `README.md`, the "checked" date in both, and the tests.

## Behaviour to preserve

- Usage counts reading-to-reading deltas. A drop in the source reading means
  the meter reset, and the new reading itself counts as the delta.
- Wh and MWh sources are converted to kWh. Unknown units are treated as kWh.
- The billing day is limited to 1-28 so every month has it. Rollover happens
  at local midnight, checked daily and on every source update. A stored period
  start that is *later* than the computed one (billing day changed) is kept
  until the computed one passes it, so changing options doesn't wipe usage.
- The stored `last_reading` is discarded if the source entity changed.
- In flat mode, crossing a band reprices all units, so the bill jumps. The
  README tells users to use **Estimated bill** ("entity tracking total costs")
  in the Energy dashboard, not **Current rate**.

## Branding

- The icon uses Sarawak flag colours (yellow `#FCD116`, red `#CE1126`, black
  `#111111`) on a yellow rounded tile: rising tariff bars, a bolt, and a
  rhinoceros hornbill with a red casque.
- **Do not imitate Sarawak Energy's logo, wordmark or brand colours.** The
  integration's name already includes the company's name, so a lookalike icon
  would look official. The README carries a not-affiliated notice; keep it.
- To change the icon, edit `scripts/make_icon.py` and run
  `python scripts/make_icon.py preview.png`. Check the preview on light and
  dark backgrounds and at about 40px.
- HACS's `brands` check is ignored in CI because the icon isn't in
  `home-assistant/brands`. Submit it there only if the repo goes into the HACS
  default store.

## Checks

```sh
python -m unittest discover tests      # tariff maths; no HA needed
python -m py_compile custom_components/sarawak_energy_tariffs/*.py
```

CI runs on every push and weekly. The HACS action needs the repo description,
topics and LICENSE to be present; all three are set. Hassfest requires
manifest keys in order: `domain`, `name`, then alphabetical.

The integration hasn't been run inside a live Home Assistant instance yet;
only the tariff maths is unit tested.

## Releasing

HACS offers updates only when a new GitHub release is published.

1. Bump `"version"` in `manifest.json` (semver).
2. Commit and push to `main`, then wait for CI to pass.
3. `gh release create vX.Y.Z --target main --title vX.Y.Z --notes "..."`.
   The tag must match the manifest version.

Release history:

- v0.1.0 (2026-10-14): first release. The LICENSE was added just after this
  tag, so it's not in the v0.1.0 download.

## Environment notes

- Developed on Windows. `.gitattributes` forces LF line endings.
- `gh` is installed and authenticated as `Atsukio`. In an already-open
  PowerShell session, refresh `PATH` from the registry if `gh` isn't found.
- Commits end with a `Co-Authored-By` trailer when an AI agent makes them.
