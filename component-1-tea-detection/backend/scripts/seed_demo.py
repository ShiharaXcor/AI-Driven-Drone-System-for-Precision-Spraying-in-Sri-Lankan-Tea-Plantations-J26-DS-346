"""Send demo scenes to the running API so the database has data to show.
Run with the server running:  python scripts/seed_demo.py
"""
import httpx

URL = "http://127.0.0.1:8000"
SCENES = [
    ("Clean tea",             [("tea_plant", 0.92)]),
    ("Tea with person",       [("tea_plant", 0.90), ("person", 0.65)]),
    ("Tea with animal",       [("tea_plant", 0.88), ("animal", 0.55)]),
    ("Tea beside road",       [("tea_plant", 0.90), ("road", 0.80)]),
    ("Low tea confidence",    [("tea_plant", 0.55)]),
    ("Possible person (low)", [("tea_plant", 0.90), ("person", 0.20)]),
    ("Bare soil only",        [("bare_soil", 0.85)]),
    ("No detections",         []),
]

with httpx.Client() as c:
    c.post(f"{URL}/api/missions/start", params={"name": "demo mission"})
    for name, dets in SCENES:
        body = {"detections": [{"cls": k, "conf": v} for k, v in dets]}
        r = c.post(f"{URL}/api/decide", json=body).json()
        print(f"{name:25s} -> {r['decision']:10s} {r['reason']}")
    c.post(f"{URL}/api/missions/end")


print("the  code is working")   
