# TeaGuard

**AI-Driven Drone System for Precision Spraying in Sri Lankan Tea Plantations**

A research prototype (RP Project — Year 4, Data Science) demonstrating an AI-guided agricultural drone system for tea plantations. The system detects tea plants and anomalies, classifies tea maturity, optimizes flight paths, and compensates spray direction for wind — reducing chemical wastage from indiscriminate spraying.

> This is a UI/UX prototype. All telemetry, detections, and flight data shown are simulated for demonstration purposes.

---

## Project overview

This application is Component 1's interface, extended to also host mockups of Components 2–4 for full-system demonstration during the research presentation and viva.

| Component | Name | Focus |
|---|---|---|
| 01 | Tea Plant Anomaly Detection | Real-time tea/person/animal/weed detection, spray decisioning, GPS-tracked detection mapping |
| 02 | Smart Path Optimization | DRL-based energy/mass-aware flight routing and obstacle avoidance |
| 03 | Tea Maturity Control | Two-pass mapping and prescription-guided variable-rate spraying (Young/Medium/Old) |
| 04 | Adaptive Spray Control | Wind-aware nozzle compensation using a Random Forest drift prediction model |

---

## Tech stack

- **React** (Vite)
- **Tailwind CSS v4**
- **React Router** — client-side routing
- **Lucide React** — icons

---

## Getting started

### Prerequisites

- [Node.js](https://nodejs.org) (LTS recommended)

### Installation

```bash
npm install
```

### Run the development server

```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or the port shown in your terminal).

### Build for production

```bash
npm run build
```

---

## Project structure