# TeaSpray Planner (Component 3 web app)

Energy-aware, mass-aware, collision-free mission planning for hillside tea spraying, with a live 3D mission view.

## Run (from ~/component3, venv active)
```
pip install fastapi uvicorn
cd c3app
python3 -m uvicorn backend.server:app --port 8000
```
Open http://localhost:8000 in Chrome. Add `#demo` to the address (http://localhost:8000/#demo) to load the example field and plan it automatically.

The backend needs the existing project files: `drl_agent/tea_spray_env.py`, `energy_model/calibrated_model.json` and `terrain/elevation_srtm.npy`.
It looks for them in `~/component3` (set `C3_BASE` if the project lives elsewhere, `C3_DRL` if tea_spray_env.py is elsewhere).

## New estate (Google Earth KML or latitude/longitude)
- Choose a .kml or .kmz file exported from Google Earth (a polygon = the field; points named "tree" or "tree r=3" = trees; a point named "refill" = refill point), or type a latitude and longitude and press Load area.
- The backend downloads elevation (Terrarium tiles, open SRTM-based data) and satellite imagery (Esri World Imagery, display only) for that spot, builds a 5 m terrain grid, and shows it in 3D. Needs internet the first time; tiles are cached in `c3app/cache` so the same estate works offline afterwards. Load every estate you will demo once before the day.
- Elevation data is about 30 m resolution: good enough for slopes and energy, not for individual trees. Mark trees in the KML or on the map.
- Not tested against the real map servers from my sandbox (they were blocked there): the pipeline was tested against a mock tile server with a known surface (elevation error 0.3 m).

## Use
1. Site: pick a terrain window (real SRTM data). The steepness slider exaggerates the heights to test steeper hills.
2. Field: draw the field corners on the map, add trees, place the refill point (or press Load example).
3. Drone: tank, spray speed, swath, reserve, clearance, dose.
4. Plan mission: compares a fixed route, a standard route and the optimised route on the same field.
5. 3D mission: Play streams live telemetry from the server. Drop obstacle ahead makes the server re-plan the rest of the mission.

## What the planner optimises
- Row direction and start corner (searched), tree arcs, refill sorties, battery reserve.
- Load-levelled refills: carry only the liquid still needed, split evenly over the remaining sorties (hover power grows with m^1.5).
- Refill-point advisor and a speed what-if.
- Every route is scored by the calibrated energy model, then checked for coverage (at least 98 percent of the field) and tree clearance.

## Measured results (tools/bench_fields.py, 24 random synthetic fields, 0.2-1.2 ha, real and 2.5x steeper terrain)
- Optimised vs standard route (rows along the longest edge, last tank trimmed): mean 9.8 percent less battery, median 8.5, range 1.5 to 22.6.
- Sources: load-levelled refills about 4.9 percent, refill-point advisor about 3.7 percent more, row direction about 1.7 percent.
- Tree contacts: optimised 0 on every field; a fixed route without avoidance had 47 contact steps on average.
- Coverage 94.8 to 98.2 percent (the gaps are clearance pockets round trees).
- Live obstacle re-plan on the demo field: about 0.4 percent extra battery, coverage kept at 99 percent.

## Limits (say these out loud)
- Energy model is fitted to SULEKO / Kenilworth figures and is not yet validated on a real field.
- SRTM terrain is smooth (90 m cells): slopes here are gentler than many real tea hillsides.
- Spray speed 6.4 km/h is an assumption: check the aircraft datasheet.
- Trees are circles; the live obstacle is known to the server (a real system would get it from the drone's sensors).

## API
GET /api/sites, GET /api/sites/{id}, GET /api/example/{id}, POST /api/plan, GET /api/mission/{id}/stream (server-sent events), POST /api/mission/{id}/obstacle
