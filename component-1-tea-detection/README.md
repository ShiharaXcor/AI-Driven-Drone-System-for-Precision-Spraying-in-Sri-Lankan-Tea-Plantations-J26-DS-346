# Component 1: Shadow-Aware Tea Plant and Anomaly Detection for Safe Spray Decision-Making

Part of the AI-Driven Drone System for Precision Spraying in Sri Lankan Tea Plantations
(SLIIT IT4010, J26-DS-346).

## Run the backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
cd backend
uvicorn app.main:app --reload --port 8000