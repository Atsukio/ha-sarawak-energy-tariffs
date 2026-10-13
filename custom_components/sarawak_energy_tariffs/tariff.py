"""Pure tariff maths for Sarawak Energy domestic billing.

Kept free of Home Assistant imports so it can be unit tested on its own.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

MODE_FLAT = "flat"
MODE_BLOCK = "block"

# Tariff D - Domestic, from https://www.sarawakenergy.com/customers/tariffs
# (checked 2026-10-14). One band per line as "upper_kWh:RM_per_kWh"; the last
# band must be "inf". The page lists both "1 to 100" and "1 to 150" at 18 sen,
# so they are merged into a single 0-150 band here.
DEFAULT_TIERS = "\n".join(
    (
        "150:0.18",
        "200:0.22",
        "300:0.25",
        "400:0.27",
        "500:0.295",
        "700:0.30",
        "800:0.305",
        "1300:0.31",
        "inf:0.315",
    )
)
DEFAULT_MINIMUM_CHARGE = 5.0


class TariffError(ValueError):
    """Raised when a tier definition cannot be parsed."""


@dataclass(frozen=True)
class Tier:
    """A consumption band: (lower, upper] kWh charged at `rate` RM/kWh."""

    lower: float
    upper: float
    rate: float

    @property
    def label(self) -> str:
        if math.isinf(self.upper):
            return f"Above {self.lower:g} kWh"
        return f"{self.lower:g}-{self.upper:g} kWh"


def parse_tiers(text: str) -> list[Tier]:
    """Parse "upper:rate" pairs separated by newlines or commas."""
    tiers: list[Tier] = []
    lower = 0.0
    for raw in text.replace(",", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            upper_text, rate_text = line.split(":")
            upper = float(upper_text)
            rate = float(rate_text)
        except ValueError as err:
            raise TariffError(f"Invalid tier line: {line!r}") from err
        if math.isinf(lower):
            raise TariffError("Only the last tier can be 'inf'")
        if math.isnan(upper) or upper <= lower:
            raise TariffError("Tier limits must be increasing numbers")
        if not math.isfinite(rate) or rate < 0:
            raise TariffError("Tier rates must be non-negative numbers")
        tiers.append(Tier(lower, upper, rate))
        lower = upper
    if not tiers:
        raise TariffError("At least one tier is required")
    if not math.isinf(tiers[-1].upper):
        raise TariffError("The last tier must use 'inf' as its limit")
    return tiers


def find_tier(tiers: list[Tier], usage: float) -> Tier:
    """Return the band that `usage` kWh falls into."""
    for tier in tiers:
        if usage <= tier.upper:
            return tier
    return tiers[-1]


def energy_charge(tiers: list[Tier], usage: float, mode: str) -> float:
    """Energy charge in RM before the minimum charge is applied.

    flat:  every kWh is charged at the rate of the band the total falls in
           (how Sarawak Energy words "For 1 to N units per month").
    block: each band's rate applies only to the kWh inside that band.
    """
    usage = max(usage, 0.0)
    if mode == MODE_FLAT:
        return usage * find_tier(tiers, usage).rate
    total = 0.0
    for tier in tiers:
        if usage <= tier.lower:
            break
        total += (min(usage, tier.upper) - tier.lower) * tier.rate
    return total


def bill_amount(
    tiers: list[Tier], usage: float, mode: str, minimum_charge: float
) -> float:
    """Estimated bill in RM including the minimum monthly charge."""
    return max(energy_charge(tiers, usage, mode), minimum_charge)


def period_start(now: datetime, billing_day: int) -> datetime:
    """Midnight on the most recent `billing_day` (1-28) at or before `now`."""
    start = now.replace(day=billing_day, hour=0, minute=0, second=0, microsecond=0)
    if now < start:
        if start.month == 1:
            start = start.replace(year=start.year - 1, month=12)
        else:
            start = start.replace(month=start.month - 1)
    return start
