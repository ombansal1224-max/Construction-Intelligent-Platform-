"""Epic 5a - Weather-aware site advisory (static protocols + optional live Open-Meteo lookup)."""
from __future__ import annotations

import requests

from .config import WEATHER_CONDITIONS

# status values: Go | Restrict | Suspend
ADVISORIES: dict[str, dict] = {
    "Normal": {
        "icon": "☀️", "risk": "Low", "headline": "Normal working conditions",
        "trigger": "Wind < 30 km/h, no rain, apparent temperature < 35 °C",
        "alerts": [
            {"title": "Routine start-of-shift toolbox talk", "severity": "Low",
             "detail": "Brief crews on the day's activities, exclusion zones and emergency assembly point."},
            {"title": "Daily pre-use inspections", "severity": "Low",
             "detail": "Inspect scaffolds, ladders, lifting gear, temporary electrics and excavation edges before use."},
        ],
        "operations": {
            "Crane & lifting": ("Go", "Follow the approved lift plan and load chart."),
            "Concrete pouring": ("Go", "Standard placement, vibration and curing."),
            "Work at height": ("Go", "Harness anchored 100% of the time above 1.8 m."),
            "Electrical works": ("Go", "Lock-out/tag-out and 30 mA RCD protection."),
            "Excavation": ("Go", "Check shoring and spoil set-back (>= 0.6 m)."),
            "Hot work / welding": ("Go", "Hot-work permit with fire watch."),
        },
        "curing": [
            "Begin curing within 24 h of placement; keep surfaces continuously moist.",
            "Minimum 7 days for OPC; 10-14 days with fly-ash / GGBS blended cements (IS 456 Cl. 13.5).",
            "Use ponding, wet hessian or an approved curing compound on vertical faces.",
        ],
        "ppe": ["Helmet", "Hi-vis vest", "Safety boots", "Gloves & eye protection as per task"],
        "checklist": ["Toolbox talk completed", "Scaffold tags checked", "Lifting gear certified",
                      "First-aid kit and extinguishers in place", "Housekeeping walk-through done"],
        "standards": ["OSHA 1926", "IS 456:2000", "BOCW Central Rules 1998"],
    },
    "High Wind": {
        "icon": "💨", "risk": "High", "headline": "High wind alert - suspend lifting & restrict height work",
        "trigger": "Sustained wind >= 35 km/h or gusts >= 45 km/h (IS 875 Pt 3 wind-load basis)",
        "alerts": [
            {"title": "Suspend crane operations", "severity": "Critical",
             "detail": "Stop lifts when wind exceeds the manufacturer's limit (commonly 36-45 km/h). Land loads, "
                       "retract trolley, and leave the jib free to weathervane."},
            {"title": "Secure loose materials and sheeting", "severity": "High",
             "detail": "Tie down formwork, plywood, GI sheets, scaffold boards, debris netting and bagged cement."},
            {"title": "Stop work at height and on open edges", "severity": "High",
             "detail": "Evacuate scaffolds and roof edges; check scaffold ties and brace formwork/props."},
            {"title": "Exclusion zone below façade work", "severity": "Medium",
             "detail": "Barricade fall-zones for falling objects; remove unsecured tools from slab edges."},
        ],
        "operations": {
            "Crane & lifting": ("Suspend", "Hook up, boom weather-vaned, outriggers locked."),
            "Concrete pouring": ("Restrict", "Only low-level pours with wind-breaks; watch rapid surface drying."),
            "Work at height": ("Suspend", "No scaffold, roof or edge work."),
            "Electrical works": ("Restrict", "No overhead line work; check for downed cables."),
            "Excavation": ("Go", "Continue with dust control and barricades."),
            "Hot work / welding": ("Restrict", "Hot-work only in sheltered bays with fire watch."),
        },
        "curing": [
            "Wind accelerates evaporation: erect wind-breaks and keep surfaces covered.",
            "Apply curing compound or cover with wet hessian + polythene immediately after finishing.",
            "Keep the evaporation rate below ~1 kg/m²/h (ACI 308 nomograph) to avoid plastic-shrinkage cracks.",
        ],
        "ppe": ["Helmet with chin strap", "Eye protection / goggles", "Dust mask", "Hi-vis vest"],
        "checklist": ["Cranes parked and locked", "Loose material tied down", "Scaffold ties re-inspected",
                      "Tarpaulins and hoardings secured", "Crews briefed on shelter points"],
        "standards": ["IS 875 (Part 3)", "OSHA 1926.1417", "IS 3696 (scaffolds)"],
    },
    "Heavy Rain": {
        "icon": "🌧️", "risk": "High", "headline": "Heavy rain alert - electrical, excavation & concrete protocols active",
        "trigger": "Rainfall >= 2.5 mm/h, thunderstorms or flood warning",
        "alerts": [
            {"title": "Electrical hazard mitigation", "severity": "Critical",
             "detail": "De-energise temporary distribution boards in wet zones, raise cables off the ground, verify "
                       "30 mA ELCB/RCCB, use IP65 enclosures and stop work with portable tools outdoors."},
            {"title": "Lightning protocol (30/30 rule)", "severity": "Critical",
             "detail": "If thunder follows lightning within 30 s, stop outdoor work and cranes; resume 30 min after the last thunder."},
            {"title": "Excavation and trench collapse risk", "severity": "High",
             "detail": "Evacuate pits; run dewatering, inspect shoring and slopes before re-entry (IS 3764)."},
            {"title": "Protect fresh concrete", "severity": "High",
             "detail": "Halt pours; cover placed concrete with tarpaulin. Rain-diluted surfaces raise w/c ratio and weaken the skin."},
            {"title": "Slip hazards and material protection", "severity": "Medium",
             "detail": "Provide anti-skid walkways, keep cement on raised pallets under cover, and clear drainage paths."},
        ],
        "operations": {
            "Crane & lifting": ("Restrict", "Suspend during lightning or poor visibility."),
            "Concrete pouring": ("Suspend", "Do not pour; protect fresh concrete."),
            "Work at height": ("Restrict", "Wet surfaces - only essential, anchored work."),
            "Electrical works": ("Suspend", "No outdoor live work; isolate wet circuits."),
            "Excavation": ("Suspend", "Evacuate pits, dewater and re-inspect."),
            "Hot work / welding": ("Restrict", "Indoors only, dry area, fire watch."),
        },
        "curing": [
            "Cover freshly cast concrete with tarpaulin/polythene propped clear of the surface.",
            "Rain on concrete less than ~4 h old: remove softened laitance and re-finish; on older concrete, treat as curing water.",
            "Never add water to a mix to compensate - verify slump and consider cube testing for rain-affected pours.",
        ],
        "ppe": ["Helmet", "Gum boots with steel toe", "Waterproof hi-vis jacket", "Insulating gloves for electrical tasks"],
        "checklist": ["ELCB/RCCB trip tested", "Temporary boards raised and covered", "Pumps running in pits",
                      "Concrete covered or pour cancelled", "Lightning shelter identified"],
        "standards": ["IS 3764 (excavation safety)", "OSHA 1926.404", "IS 732 (electrical wiring)"],
    },
    "Extreme Heat": {
        "icon": "🔥", "risk": "High", "headline": "Extreme heat alert - heat-stress controls & hot-weather concreting",
        "trigger": "Apparent temperature >= 40 °C or ambient >= 38 °C",
        "alerts": [
            {"title": "Heat-stress management", "severity": "Critical",
             "detail": "Provide 250 ml of water every 20 min, ORS, shaded rest bays; enforce work-rest cycles and buddy checks."},
            {"title": "Reschedule heavy work", "severity": "High",
             "detail": "Shift strenuous tasks to 6-11 am and after 4 pm; avoid exposed roof/slab work from 12-3 pm."},
            {"title": "Hot-weather concreting", "severity": "High",
             "detail": "Pour at night or early morning, use chilled water/ice and retarding admixtures, keep placing "
                       "temperature <= 35 °C and dampen subgrade and formwork (IS 7861 Pt 1, ACI 305R)."},
            {"title": "Hot surfaces and fire risk", "severity": "Medium",
             "detail": "Exposed steel and formwork cause burns; keep flammables shaded and extinguishers close at hand."},
        ],
        "operations": {
            "Crane & lifting": ("Go", "Check hydraulic oil temperatures; relieve operators regularly."),
            "Concrete pouring": ("Restrict", "Night / early-morning pours only, with hot-weather controls."),
            "Work at height": ("Restrict", "Short shifts, shaded breaks, harness comfort checks."),
            "Electrical works": ("Restrict", "Overloaded cables overheat - de-rate and inspect."),
            "Excavation": ("Restrict", "Limit manual digging; rotate crews every 30-45 min."),
            "Hot work / welding": ("Restrict", "Early hours only, fire watch, hydrate."),
        },
        "curing": [
            "Cure for at least 10 days in hot, dry weather (IS 456 Cl. 13.5.1), extend to 14 days with blended cements.",
            "Start curing immediately after finishing; use fogging, wet hessian and reflective covers.",
            "Shade aggregates, paint water tanks/pipes white and keep mixer drums cool to limit concrete temperature.",
        ],
        "ppe": ["Ventilated helmet with neck shade", "Light-colour breathable hi-vis", "UV eye protection", "Cooling vest / towel"],
        "checklist": ["Water and ORS stations stocked", "Shaded rest areas set up", "Work shifted to cooler hours",
                      "Heat-illness first-aid briefed", "Concrete temperature logged before each pour"],
        "standards": ["IS 456:2000 Cl. 13.5", "IS 7861 (Part 1)", "OSHA heat-illness guidance"],
    },
}

_RISK_ORDER = {"Normal": 0, "Extreme Heat": 1, "High Wind": 2, "Heavy Rain": 3}


def get_advisory(condition: str) -> dict:
    if condition not in ADVISORIES:
        raise ValueError(f"Unknown weather condition: {condition}. Options: {', '.join(WEATHER_CONDITIONS)}")
    return ADVISORIES[condition]


def classify_conditions(wind_kmh: float, gust_kmh: float, rain_mm_h: float, apparent_temp_c: float) -> str:
    """Map live readings to the most dangerous applicable advisory."""
    flags = []
    if rain_mm_h >= 2.5:
        flags.append("Heavy Rain")
    if wind_kmh >= 35 or gust_kmh >= 45:
        flags.append("High Wind")
    if apparent_temp_c >= 40:
        flags.append("Extreme Heat")
    return max(flags, key=lambda f: _RISK_ORDER[f]) if flags else "Normal"


def fetch_live_weather(city: str, timeout: int = 10) -> dict:
    """Open-Meteo geocoding + current weather (free, keyless). Raises RuntimeError on failure."""
    if not city.strip():
        raise RuntimeError("Enter a city name.")
    try:
        geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                           params={"name": city.strip(), "count": 1}, timeout=timeout)
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            raise RuntimeError(f"City '{city}' not found.")
        place = results[0]
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
                    "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m"},
            timeout=timeout)
        wx.raise_for_status()
        cur = wx.json()["current"]
    except requests.RequestException as exc:
        raise RuntimeError(f"Weather service unavailable: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise RuntimeError("Unexpected weather response.") from exc

    reading = {
        "location": f"{place['name']}, {place.get('admin1', '')}, {place.get('country', '')}".replace(" ,", ""),
        "temperature_c": cur["temperature_2m"], "apparent_temperature_c": cur["apparent_temperature"],
        "precipitation_mm": cur["precipitation"], "wind_kmh": cur["wind_speed_10m"],
        "gusts_kmh": cur["wind_gusts_10m"],
    }
    reading["suggested_condition"] = classify_conditions(
        reading["wind_kmh"], reading["gusts_kmh"], reading["precipitation_mm"], reading["apparent_temperature_c"])
    return reading
