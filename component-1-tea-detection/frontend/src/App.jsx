import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";

// Entry screens
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

// Dashboard shell
import DashboardLayout from "./layouts/DashboardLayout";

// Component 1 — Tea Plant Anomaly Detection
import DetectionHome from "./pages/detection/Home";
import DetectionMap from "./pages/detection/DetectionMap";
import DetectionLogs from "./pages/detection/Logs";
import DetectionAlerts from "./pages/detection/Alerts";
import DetectionManualControl from "./pages/detection/ManualControl";
import DetectionSettings from "./pages/detection/Settings";

// Component 2 — Smart Path Optimization (stub, not yet built)
import FlightLiveMission from "./pages/flight/LiveMission";
import FlightMissionPlanner from "./pages/flight/MissionPlanner";
import FlightAnalytics from "./pages/flight/FlightAnalytics";
import FlightEstates from "./pages/flight/Estates";

// Component 3 — Tea Maturity Control
import MappingHome from "./pages/mapping/Home";
import MappingMissions from "./pages/mapping/Missions";
import MappingPrescription from "./pages/mapping/Prescription";
import MappingFlight from "./pages/mapping/Flight";
import MappingSettings from "./pages/mapping/Settings";

// Component 4 — Adaptive Spray Control (stub, not yet built)
import SprayMissionSetup from "./pages/spray/MissionSetup";
import SprayWindMonitor from "./pages/spray/WindMonitor";
import SprayCompensation from "./pages/spray/SprayCompensation";
import SprayPerformance from "./pages/spray/Performance";

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {/* Entry flow */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Dashboard */}
          <Route path="/dashboard" element={<DashboardLayout />}>
            {/* Component 1 — Tea Plant Anomaly Detection */}
            <Route path="detection" element={<DetectionHome />} />
            <Route path="detection/map" element={<DetectionMap />} />
            <Route path="detection/logs" element={<DetectionLogs />} />
            <Route path="detection/alerts" element={<DetectionAlerts />} />
            <Route path="detection/manual" element={<DetectionManualControl />} />
            <Route path="detection/settings" element={<DetectionSettings />} />

            {/* Component 2 — Smart Path Optimization */}
           <Route path="flight" element={<FlightLiveMission />} />
<Route path="flight/planner" element={<FlightMissionPlanner />} />
<Route path="flight/analytics" element={<FlightAnalytics />} />
<Route path="flight/estates" element={<FlightEstates />} />

            {/* Component 3 — Tea Maturity Control */}
            <Route path="mapping" element={<MappingHome />} />
            <Route path="mapping/missions" element={<MappingMissions />} />
            <Route path="mapping/prescription" element={<MappingPrescription />} />
            <Route path="mapping/flight" element={<MappingFlight />} />
            <Route path="mapping/settings" element={<MappingSettings />} />

            {/* Component 4 — Adaptive Spray Control */}
            <Route path="spray" element={<SprayMissionSetup />} />
<Route path="spray/wind" element={<SprayWindMonitor />} />
<Route path="spray/compensation" element={<SprayCompensation />} />
<Route path="spray/performance" element={<SprayPerformance />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}