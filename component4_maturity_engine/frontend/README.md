# Component 4 — Frontend (standalone)

React + Vite + Tailwind dashboard for **Maturity-Driven Variable-Rate Spraying**.
Same look as the team TeaDrone prototype, but only Component 4 pages, so it can be
developed and demonstrated before full system integration.

| Page | What it does |
|---|---|
| Home | model status, active spray rules, recent missions |
| Prescription | upload mapping photos → maturity per photo → spray prescription grid, JSON/CSV download |
| Missions | history of all prescriptions |
| Model | test-set metrics, confusion matrix, adaptive vs fixed-rate comparison |
| Settings | edit maturity → spray rules (saved to `configs/spray_mapping.yaml`) |

## Run

Terminal 1 — API (from `component4_maturity_engine/`, venv active):
```
uvicorn api.server:app --reload --port 8000
```
Terminal 2 — frontend (from `component4_maturity_engine/frontend/`):
```
npm install
npm run dev
```
Open http://localhost:5173. In development, Vite forwards `/api` to port 8000 (see `vite.config.js`).

## Integration later
Pages in `src/pages/` only depend on `src/api/c4.js`, `useC4Styles.js` and the theme tokens in
`src/index.css`, which are the same as `prototype-ui/teaguard-prototype`. To merge, copy the
pages into `prototype-ui/.../src/pages/mapping/` and add their routes.
