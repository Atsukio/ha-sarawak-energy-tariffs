# Sarawak Energy Tariffs for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/Atsukio/ha-sarawak-energy-tariffs/actions/workflows/validate.yml/badge.svg)](https://github.com/Atsukio/ha-sarawak-energy-tariffs/actions/workflows/validate.yml)

A custom integration that prices your electricity usage with the tiered
Sarawak Energy domestic tariff (Tariff D). You give it any cumulative kWh
sensor. It counts your usage for the current billing cycle and shows your
current tier, rate and estimated bill.

## Sensors

| Sensor | Unit | Notes |
| --- | --- | --- |
| Billing period usage | kWh | Resets on your billing day |
| Estimated bill | MYR | Includes the RM 5.00 minimum charge. Attributes show the energy charge and whether the minimum applied |
| Current rate | MYR/kWh | Rate for the band you are in now. Attributes: `tier`, `kwh_to_next_tier` |
| Current tier | - | e.g. `150-200 kWh` |

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Atsukio&repository=ha-sarawak-energy-tariffs&category=integration)

Or add it by hand:

1. In HACS, open the **⋮** menu and choose **Custom repositories**.
2. Add `https://github.com/Atsukio/ha-sarawak-energy-tariffs` with type **Integration**.
3. Search for **Sarawak Energy Tariffs**, download it, then restart Home Assistant.

### Manual

Copy `custom_components/sarawak_energy_tariffs` into your
`config/custom_components/` folder, then restart.

### Add the integration

Go to **Settings → Devices & services → Add integration → Sarawak Energy Tariffs**.

## Configuration

- **Energy sensor**: a cumulative energy sensor in Wh, kWh or MWh, such as your
  smart meter's grid import or a `utility_meter`. If the sensor resets, the
  integration notices and keeps counting.
- **Billing cycle start day**: the day of the month your bill period starts (1-28).
- **How tiers are charged**:
  - *Flat* (default): every kWh is charged at the rate of the band your total
    falls in. This matches Sarawak Energy's "For 1 to N units per month" wording.
  - *Block*: each band's rate applies only to the kWh inside that band.
- **Tiers**: one `upper_kWh:RM_per_kWh` per line, ending with `inf:rate`. The
  defaults come from the
  [Sarawak Energy tariff page](https://www.sarawakenergy.com/customers/tariffs)
  as checked on 2026-10-14:

  ```
  150:0.18
  200:0.22
  300:0.25
  400:0.27
  500:0.295
  700:0.30
  800:0.305
  1300:0.31
  inf:0.315
  ```

To change any of these later, use **Configure** on the integration.

> The tariff page doesn't say whether bands are charged flat or in blocks.
> Compare the *Estimated bill* sensor with a real bill and switch modes if they
> don't match.

## Energy dashboard

Under **Settings → Dashboards → Energy → Grid consumption**, choose
**Use an entity tracking the total costs** and select **Estimated bill**.
This works in both modes. In flat mode, crossing into a higher band reprices
every unit already used, so the cost jumps at that point. This is expected.

Avoid **Use an entity with current price** in flat mode. That option
multiplies each new kWh by the current rate, so it misses the repricing jump.

## Limitations

- Usage while Home Assistant is down is still counted, because the next
  reading includes it. If a billing day passes during downtime, that usage
  goes to the new period.
- In block mode, the *Current rate* at an exact band boundary shows the lower
  band's rate.

## Development

The tariff maths in `tariff.py` doesn't depend on Home Assistant:

```sh
python -m unittest discover tests
```
