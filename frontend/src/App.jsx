import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import DetectionPage from './pages/detection/DetectionPage'
import WindPage from './pages/wind/WindPage'
import PathPage from './pages/path/PathPage'
import MaturityPage from './pages/maturity/MaturityPage'

function Home() {
  return <p>Choose a component from the menu.</p>
}

function App() {
  return (
    <BrowserRouter>
      <header>
        <h1>TeaDrone</h1>
        <nav style={{ display: 'flex', gap: '1rem' }}>
          <NavLink to="/">Home</NavLink>
          <NavLink to="/detection">C1 - Spray detection</NavLink>
          <NavLink to="/wind">C2 - Wind handling</NavLink>
          <NavLink to="/path">C3 - Smart path</NavLink>
          <NavLink to="/maturity">C4 - Maturity</NavLink>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/detection" element={<DetectionPage />} />
          <Route path="/wind" element={<WindPage />} />
          <Route path="/path" element={<PathPage />} />
          <Route path="/maturity" element={<MaturityPage />} />
          <Route path="*" element={<p>Page not found</p>} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App