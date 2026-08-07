"""
Heat stress risk engine for Heat-Shield.

Two stages:
1. heat_index_c() — NOAA/Rothfusz regression heat index, the actual formula
   used by the US National Weather Service. Same math the industry uses
   for heat advisories, just computed server-side from real weather data
   instead of being simulated in the browser.
2. calculate_risk() — combines the heat index with worker-reported context
   (work intensity, clothing, hydration, time since last break, health
   conditions) into a single 0-100 score. Thresholds/categories mirror
   OSHA/NIOSH heat-illness risk tiers.
"""

WORK_TYPE_ADD = {"heavy": 24, "moderate": 12, "light": 0}
CLOTHING_ADD = {"heavy": 12, "light": 0}
HEALTH_ADD = {"cardiac": 15, "other": 6, "none": 0}


def heat_index_c(temp_c: float, humidity: float) -> float:
    """NOAA Rothfusz regression. Input/output in Celsius."""
    t_f = temp_c * 9 / 5 + 32
    rh = humidity

    # Simple formula is close enough below 80F; full regression above that.
    hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))

    if (hi_f + t_f) / 2 >= 80:
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 0.00683783 * t_f * t_f
            - 0.05481717 * rh * rh
            + 0.00122874 * t_f * t_f * rh
            + 0.00085282 * t_f * rh * rh
            - 0.00000199 * t_f * t_f * rh * rh
        )
        if rh < 13 and 80 <= t_f <= 112:
            hi_f -= ((13 - rh) / 4) * ((17 - abs(t_f - 95)) / 17) ** 0.5
        elif rh > 85 and 80 <= t_f <= 87:
            hi_f += ((rh - 85) / 10) * ((87 - t_f) / 5)

    return round((hi_f - 32) * 5 / 9, 1)


def base_score_from_heat_index(hi_c: float) -> int:
    """Maps heat index to a base score using OSHA/NIOSH-style risk bands."""
    if hi_c < 27:
        return 12
    elif hi_c < 32:
        return 28  # Caution
    elif hi_c < 39:
        return 45  # Extreme Caution
    elif hi_c < 51:
        return 70  # Danger
    else:
        return 90  # Extreme Danger


def calculate_risk(
    temp_c: float,
    humidity: float,
    work_type: str = "moderate",
    clothing: str = "light",
    hydration_glasses: int = 3,
    rest_minutes: int = 45,
    health: str = "none",
) -> dict:
    hi = heat_index_c(temp_c, humidity)
    score = base_score_from_heat_index(hi)

    score += WORK_TYPE_ADD.get(work_type, 0)
    score += CLOTHING_ADD.get(clothing, 0)
    score += HEALTH_ADD.get(health, 0)
    score += max(0, 4 - hydration_glasses) * 5
    score += max(0, (rest_minutes - 60) / 10) * 3

    score = int(round(min(100, max(0, score))))

    if score < 40:
        label, level = "LOW RISK", "low"
        desc = "Conditions are manageable. Maintain normal hydration schedule."
    elif score < 70:
        label, level = "MODERATE RISK", "moderate"
        desc = "Take a shaded break within 15 minutes and increase water intake."
    else:
        label, level = "HIGH RISK", "high"
        desc = "Stop heavy activity now. Move to shade, hydrate, and await check-in."

    recommendations = []
    if score >= 85:
        recommendations.append("Stop work immediately and move to a shaded or cooled area.")
        recommendations.append("Supervisor and emergency contact are being notified now.")
    elif score >= 70:
        recommendations.append("Take a 15-minute shaded rest break as soon as possible.")
        recommendations.append("Drink 2 glasses of water in the next 20 minutes.")
    elif score >= 40:
        recommendations.append("Plan a shaded break within the hour.")
        recommendations.append("Keep sipping water even if not thirsty.")
    else:
        recommendations.append("No immediate action needed — conditions are within safe range.")

    if rest_minutes > 90:
        recommendations.append(f"It has been {rest_minutes} minutes since your last break — schedule one soon.")
    if hydration_glasses < 3:
        recommendations.append("Hydration is below the recommended pace for this heat index.")
    if health == "cardiac":
        recommendations.append("Reported cardiac/BP condition — thresholds have been tightened for your profile.")

    return {
        "heat_index_c": hi,
        "score": score,
        "label": label,
        "level": level,
        "description": desc,
        "recommendations": recommendations,
        "alert": score >= 85,
    }
