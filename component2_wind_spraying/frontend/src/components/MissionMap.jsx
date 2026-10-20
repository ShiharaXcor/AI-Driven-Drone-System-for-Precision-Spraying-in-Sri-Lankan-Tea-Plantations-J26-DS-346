import { useMemo } from "react";
import { MapContainer, TileLayer, Polygon, Polyline, CircleMarker, Marker, LayersControl, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Drone icon: an arrow rotated to the flight heading
const droneIcon = (heading, hold) =>
  L.divIcon({
    className: "",
    html: `<div class="drone-icon ${hold ? "hold" : ""}" style="transform: rotate(${heading}deg)">▲</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

export default function MissionMap({ mission, idx }) {
  const step = mission.steps[idx];
  const sofar = mission.steps.slice(0, idx + 1);

  const track = useMemo(() => sofar.map((s) => s.drone), [mission, idx]);         // eslint-disable-line
  const sprayed = useMemo(() => sofar.filter((s, i) => s.status === "SPRAYING" && i % 2 === 0), [mission, idx]); // eslint-disable-line

  return (
    <div className="map-wrap">
      <MapContainer key={JSON.stringify(mission.field)} bounds={mission.field} boundsOptions={{ padding: [30, 30] }} scrollWheelZoom className="map">
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Satellite">
            <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                       attribution="Tiles &copy; Esri" maxZoom={20} maxNativeZoom={19} />
          </LayersControl.BaseLayer>
          <LayersControl.BaseLayer name="Map">
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                       attribution="&copy; OpenStreetMap contributors" maxZoom={20} maxNativeZoom={19} />
          </LayersControl.BaseLayer>
        </LayersControl>

        <Polygon positions={mission.field} pathOptions={{ color: "#f0efec", weight: 2, fillColor: "#1baf7a", fillOpacity: 0.12 }} />

        {/* planned spray lines */}
        {mission.lines.map((l) => (
          <Polyline key={l.index} positions={[l.start, l.end]} pathOptions={{ color: "#ffffff", weight: 1, opacity: 0.7, dashArray: "3 6" }} />
        ))}

        {/* where the spray lands: red = without correction, green = with correction */}
        {sprayed.map((s, i) => (
          <CircleMarker key={`u${i}`} center={s.land_uncorrected} radius={2.5}
                        pathOptions={{ color: "#e34948", fillColor: "#e34948", fillOpacity: 0.9, weight: 0 }} />
        ))}
        {sprayed.map((s, i) => (
          <CircleMarker key={`c${i}`} center={s.land_corrected} radius={2.5}
                        pathOptions={{ color: "#1baf7a", fillColor: "#2fd394", fillOpacity: 0.95, weight: 0 }} />
        ))}

        {/* actual (corrected) flight track */}
        <Polyline positions={track} pathOptions={{ color: "#3987e5", weight: 2.5 }} />

        <Marker position={step.drone} icon={droneIcon(step.heading_deg, step.status === "HOLD")}>
          <Tooltip direction="top" offset={[0, -12]}>
            Line {step.line} · {step.status} · tilt {step.nozzle_tilt_deg}° {step.nozzle_tilt_side || ""}
          </Tooltip>
        </Marker>
      </MapContainer>

      {/* wind compass: arrow points where the wind blows TO */}
      <div className="compass" aria-label={`Wind ${step.wind_ms} m/s from ${step.wind_dir_deg} degrees`}>
        <div className="compass-n">N</div>
        <div className="compass-arrow" style={{ transform: `rotate(${(step.wind_dir_deg + 180) % 360}deg)` }}>➜</div>
        <div className="compass-label">{step.wind_ms} m/s</div>
      </div>

      <ul className="map-legend">
        <li><span className="dot" style={{ background: "#e34948" }} /> spray without correction</li>
        <li><span className="dot" style={{ background: "#2fd394" }} /> spray with correction</li>
        <li><span className="line" style={{ borderTopColor: "#3987e5" }} /> drone track</li>
        <li><span className="line dashed" /> planned lines</li>
      </ul>
    </div>
  );
}
