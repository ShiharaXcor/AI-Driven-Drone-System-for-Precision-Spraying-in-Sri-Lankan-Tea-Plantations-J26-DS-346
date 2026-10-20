# Component 4 API — connects the TeaDrone dashboard to the model

The Component 4 frontend (`frontend/`)
calls this API to classify mapping photos and build spray prescriptions.

## Run (two terminals)

**1 — API** (from `component4_maturity_engine/`, venv active):
```
pip install fastapi "uvicorn[standard]" python-multipart
uvicorn api.server:app --reload --port 8000
```
Needs the trained model at `runs/effnet_b0/best.pt` (copy `C4_data/runs/` from Drive into `runs/`).
Check http://localhost:8000/api/health → `"model_loaded": true`. Interactive docs: http://localhost:8000/docs

**2 — Frontend** (from `component4_maturity_engine/frontend/`):
```
npm install
npm run dev
```
Open http://localhost:5173

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| GET | /api/health | model status |
| GET / PUT | /api/config | maturity → spray rules (validated, saved to `configs/spray_mapping.yaml`) |
| POST | /api/prescriptions | upload photos → new mission + prescription |
| GET | /api/missions, /api/missions/{id} | mission history / one prescription |
| GET | /api/missions/{id}/images/{n} | region thumbnail |
| GET | /api/metrics | test results of trained models + fixed-rate comparison |

Missions are stored in `data/missions/` (not committed).
