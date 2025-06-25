import requests, os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL")
GEMINI_KEY = os.getenv("GEMINI_KEY")

compare_emission_factors = {"diesel": 1.0, "petrol": 1.05, "electric": 0.20}

travel_mode_map = {
    "car": "DRIVE",
    "truck": "DRIVE",  # Google treats it similarly to car for routing
    "bike": "BICYCLE",
    "walk": "WALK",
    "flight": "TRANSIT",  # Use TRANSIT for flights or mixed travel
}

EMISSION_FACTORS = {
    "truck": {
        "diesel": {
            "flat": {"highway": {"TTW": 0.13, "WTT": 0.03}, "city": {"TTW": 0.12, "WTT": 0.028}},
            "hilly": {"highway": {"TTW": 0.15, "WTT": 0.035}, "city": {"TTW": 0.14, "WTT": 0.032}}
        },
        "petrol": {
            "flat": {"highway": {"TTW": 0.12, "WTT": 0.025}, "city": {"TTW": 0.11, "WTT": 0.023}},
            "hilly": {"highway": {"TTW": 0.14, "WTT": 0.03}, "city": {"TTW": 0.13, "WTT": 0.028}}
        },
        "electric": {
            "flat": {"highway": {"TTW": 0.01, "WTT": 0.015}, "city": {"TTW": 0.009, "WTT": 0.013}},
            "hilly": {"highway": {"TTW": 0.012, "WTT": 0.017}, "city": {"TTW": 0.011, "WTT": 0.016}}
        }
    },

    "car": {
        "diesel": {
            "flat": {"highway": {"TTW": 0.09, "WTT": 0.02}, "city": {"TTW": 0.08, "WTT": 0.018}},
            "hilly": {"highway": {"TTW": 0.10, "WTT": 0.022}, "city": {"TTW": 0.09, "WTT": 0.02}}
        },
        "petrol": {
            "flat": {"highway": {"TTW": 0.08, "WTT": 0.018}, "city": {"TTW": 0.07, "WTT": 0.016}},
            "hilly": {"highway": {"TTW": 0.09, "WTT": 0.02}, "city": {"TTW": 0.08, "WTT": 0.018}}
        },
        "electric": {
            "flat": {"highway": {"TTW": 0.005, "WTT": 0.010}, "city": {"TTW": 0.0045, "WTT": 0.009}},
            "hilly": {"highway": {"TTW": 0.006, "WTT": 0.012}, "city": {"TTW": 0.0055, "WTT": 0.011}}
        }
    },
    
    "bike": {
        "petrol": {
            "flat": {"highway": {"TTW": 0.05, "WTT": 0.012}, "city": {"TTW": 0.045, "WTT": 0.011}},
            "hilly": {"highway": {"TTW": 0.055, "WTT": 0.014}, "city": {"TTW": 0.05, "WTT": 0.013}}
        },
        "electric": {
            "flat": {"highway": {"TTW": 0.003, "WTT": 0.008}, "city": {"TTW": 0.0025, "WTT": 0.0075}},
            "hilly": {"highway": {"TTW": 0.0035, "WTT": 0.009}, "city": {"TTW": 0.003, "WTT": 0.0085}}
        }
    },
    
    "flight": {
        "JetFuel": {
            "default": {"default": {"TTW": 0.55, "WTT": 0.16}}
        }
    }
}

def get_city_name(lat, lon):
    try:    
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json"
        }
        headers = {
            "User-Agent": f"GreenRouteApp/1.0 ({CONTACT_EMAIL})"
        }
        response = requests.get(url, params=params, headers=headers)
        try:
            village = response.json()['address']['village']
        except Exception as e:
            try:
                village = response.json()['address']['town']
            except Exception as e:
                village = response.json()['address']['city_district']
        return village
    except:
        return "Unknown"

def calculate_emissions(vehicle_type, fuel_type, load_weight_ton, distance_km, terrain, road_type):
    try:
        if vehicle_type != "flight":
            factors = EMISSION_FACTORS[vehicle_type][fuel_type][terrain][road_type]
        else:
            factors = EMISSION_FACTORS[vehicle_type][fuel_type]['default']['default']
    except KeyError:
        return {"TTW": 0, "WTT": 0, "WTW": 0}

    ttw = factors["TTW"] * distance_km * load_weight_ton
    wtt = factors["WTT"] * distance_km * load_weight_ton
    return {"TTW": round(ttw, 2), "WTT": round(wtt, 2), "WTW": round(ttw + wtt, 2)}
