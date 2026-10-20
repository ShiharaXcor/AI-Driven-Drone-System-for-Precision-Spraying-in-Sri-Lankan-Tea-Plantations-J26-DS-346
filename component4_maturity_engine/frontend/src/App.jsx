import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Prescription from "./pages/Prescription";
import Missions from "./pages/Missions";
import Model from "./pages/Model";
import Settings from "./pages/Settings";

// Component 4 standalone frontend. The pages use the same API and theme tokens as
// the team prototype, so they can be moved into prototype-ui at integration.
export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/prescription" element={<Prescription />} />
            <Route path="/missions" element={<Missions />} />
            <Route path="/model" element={<Model />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Home />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
