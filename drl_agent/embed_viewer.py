# embed_viewer.py - bake route files into the viewer so the demo opens with no loading step.
# Run:  python3 drl_agent/embed_viewer.py viewer.html demo.html planner_output/routes_5001.json planner_output/routes_5003.json ...
import sys, json
src, dst, files = sys.argv[1], sys.argv[2], sys.argv[3:]
html = open(src, encoding="utf-8").read()
data = [json.load(open(f, encoding="utf-8")) for f in files]
tag = "window.EMBED = []; /*EMBED*/"
assert tag in html, "viewer.html does not contain the embed marker"
open(dst, "w", encoding="utf-8").write(html.replace(tag, "window.EMBED = " + json.dumps(data) + "; /*EMBED*/"))
print(f"wrote {dst} with {len(data)} file(s)")