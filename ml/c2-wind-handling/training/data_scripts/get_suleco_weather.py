"""
Download hourly weather for the places and dates of the Suleco flights
(Open-Meteo historical archive - free, no API key, no extra packages).

Suleco flights (May-Aug 2026) were in 3 districts. We use the main town
of each district as the weather point (Open-Meteo works on a ~10 km grid).

Output:  claude\\suleco_weather.csv
Run:
    cd C:\\Users\\bihar\\OneDrive\\Desktop\\SLIIT\\claude\\automation
    python get_suleco_weather.py
"""
import csv
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "suleco_weather.csv")

DISTRICTS = {                      # district town coordinates
    "Ampara": (7.2975, 81.6820),
    "Badulla": (6.9934, 81.0550),
    "Polonnaruwa": (7.9403, 81.0188),
}
START, END = "2026-05-01", "2026-08-31"
VARS = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
        "wind_direction_10m", "wind_gusts_10m", "precipitation"]

rows = []
for name, (lat, lon) in DISTRICTS.items():
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={START}&end_date={END}"
           f"&hourly={','.join(VARS)}&wind_speed_unit=ms&timezone=Asia%2FColombo")
    print(f"Downloading {name} ...", flush=True)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                data = json.load(r)["hourly"]
            break
        except Exception as e:
            print("   retrying:", e)
            time.sleep(5)
    else:
        raise SystemExit(f"Could not download {name}")
    for i, t in enumerate(data["time"]):
        rows.append([t, name] + [data[v][i] for v in VARS])
    print(f"   {len(data['time'])} hours")

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["datetime", "district", "temp_c", "rh_pct", "wind_speed_10m_ms",
                "wind_dir_deg", "wind_gust_10m_ms", "precip_mm"])
    w.writerows(rows)
print(f"Saved {len(rows)} rows to {OUT}")
