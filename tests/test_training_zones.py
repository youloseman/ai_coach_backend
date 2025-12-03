import math

from training_zones import (
    calculate_running_zones_from_race,
    calculate_swimming_zones_from_css,
    calculate_cycling_zones_from_ftp,
)


def test_running_zones_from_half_marathon():
    """
    Basic sanity check for running zones calculation from a half-marathon.
    """
    # 21.1 km in 1:30:00 -> 5400 seconds
    zones = calculate_running_zones_from_race(
        distance_km=21.1,
        time_seconds=5400,
        race_type="HM",
    )

    data = zones.to_dict()

    # Threshold pace should be finite and positive
    assert data["threshold_pace_per_km_seconds"] > 0

    # All zones should be present
    for key in ["z1", "z2", "z3", "z4", "z5"]:
        assert key in data
        assert "min_pace" in data[key]
        assert "max_pace" in data[key]
        assert isinstance(data[key]["description"], str)


def test_cycling_zones_from_ftp_monotonic():
    """
    Cycling zones should be ordered by increasing intensity.
    """
    ftp = 250.0
    zones = calculate_cycling_zones_from_ftp(ftp)
    data = zones.to_dict()

    # Check that zone wattage ranges grow with zone number
    z1 = data["z1"]
    z2 = data["z2"]
    z3 = data["z3"]
    z4 = data["z4"]
    z5 = data["z5"]

    assert z1["min_watts"] <= z1["max_watts"] < z2["min_watts"] <= z2["max_watts"]
    assert z2["max_watts"] < z3["min_watts"] <= z3["max_watts"]
    assert z3["max_watts"] < z4["min_watts"] <= z4["max_watts"]
    assert z4["max_watts"] < z5["min_watts"] <= z5["max_watts"]


def test_swimming_zones_from_css_relative_to_css():
    """
    Swimming zones should be reasonably spaced around CSS pace.
    """
    css_seconds = 90.0  # 1:30 / 100m
    zones = calculate_swimming_zones_from_css(css_seconds)
    data = zones.to_dict()

    # CSS itself
    css_from_dict = data["css_pace_per_100m_seconds"]
    assert math.isclose(css_from_dict, css_seconds)

    # Zone 1 pace should be slower (bigger seconds per 100m) than CSS
    # Zone 5 pace should be faster (smaller seconds per 100m) than CSS
    # We just check they are not equal in the wrong direction by parsing back numbers.
    # Pace strings are "M:SS/100m"
    def parse_swim_pace(p: str) -> int:
        minutes, rest = p.split(":")
        seconds = rest.split("/")[0]
        return int(minutes) * 60 + int(seconds)

    z1_pace = parse_swim_pace(data["z1"]["pace"])
    z3_pace = parse_swim_pace(data["z3"]["pace"])
    z5_pace = parse_swim_pace(data["z5"]["pace"])

    assert z1_pace > css_seconds
    assert z3_pace == css_seconds
    assert z5_pace < css_seconds


