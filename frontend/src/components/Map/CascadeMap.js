import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMap } from 'react-leaflet';
import './CascadeMap.css';

const SUTLEJ_CENTRE = [30.75, 75.0];
const ZOOM = 9;

function severityColor(s) {
  if (s >= 0.75) return '#ff0000';
  if (s >= 0.50) return '#f85149';
  if (s >= 0.30) return '#d29922';
  return '#3fb950';
}

function severityLabel(s) {
  if (s >= 0.75) return 'CRITICAL';
  if (s >= 0.50) return 'HIGH';
  if (s >= 0.30) return 'MODERATE';
  return 'LOW';
}

function edgeColor(edge) {
  if (!edge.passable) return '#f85149';
  if (edge.edge_type === 'river') return '#388bfd';
  if (edge.edge_type === 'drainage') return '#39d353';
  return edge.degradation_factor < 0.5 ? '#d29922' : '#484f58';
}

// Pulse animation control
function PulseSvg({ color }) {
  return (
    <svg width="24" height="24" style={{ overflow: 'visible' }}>
      <circle cx="12" cy="12" r="6" fill={color} opacity="0.9" />
    </svg>
  );
}

export default function CascadeMap({ cascade, zones, onZoneClick, selectedZone, mlPredictions = {} }) {
  if (!cascade) return null;

  const nodeMap = {};
  zones.forEach(z => { nodeMap[z.id] = z; });

  return (
    <MapContainer
      center={SUTLEJ_CENTRE}
      zoom={ZOOM}
      className="leaflet-map"
      zoomControl={true}
    >
      {/* Dark base tile layer */}
      <TileLayer
        attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
      />

      {/* Zone edges */}
      {cascade.edges && cascade.edges.map((edge, i) => {
        const from = nodeMap[edge.from];
        const to = nodeMap[edge.to];
        if (!from || !to) return null;
        return (
          <Polyline
            key={i}
            positions={[[from.lat, from.lon], [to.lat, to.lon]]}
            pathOptions={{
              color: edgeColor(edge),
              weight: edge.edge_type === 'river' ? 3 : 1.5,
              opacity: edge.passable ? 0.7 : 0.4,
              dashArray: edge.passable ? null : '4 4',
            }}
          />
        );
      })}

      {/* Zone nodes */}
      {cascade.nodes && cascade.nodes.map(node => {
        const zone = nodeMap[node.id];
        if (!zone) return null;
        const color = severityColor(node.severity_score);
        const radius = 8 + node.vulnerability_index * 8;
        const isSelected = selectedZone && selectedZone.id === node.id;

        const mlPred = mlPredictions[node.id];

        return (
          <CircleMarker
            key={node.id}
            center={[zone.lat, zone.lon]}
            radius={radius}
            pathOptions={{
              color: isSelected ? '#fff' : color,
              fillColor: color,
              fillOpacity: 0.85,
              weight: isSelected ? 3 : 1.5,
            }}
            eventHandlers={{ click: () => onZoneClick(zone) }}
          >
            <Popup className="cascade-popup">
              <div className="popup-header">
                <strong>{zone.name}</strong>
                <span className={`badge badge-${severityLabel(node.severity_score).toLowerCase()}`}>
                  {severityLabel(node.severity_score)}
                </span>
              </div>
              <div className="popup-body">
                <div className="popup-row">
                  <span>Severity</span>
                  <span>{(node.severity_score * 100).toFixed(0)}%</span>
                </div>
                <div className="popup-row">
                  <span>ICS Confidence</span>
                  <span>{(node.incident_confidence * 100).toFixed(0)}%</span>
                </div>
                <div className="popup-row">
                  <span>Vulnerability</span>
                  <span>{(node.vulnerability_index * 100).toFixed(0)}%</span>
                </div>

                {/* ML Flood Risk — only shown when model is available */}
                {mlPred && (
                  <div className="popup-row popup-ml-row">
                    <span>🤖 ML Flood Risk</span>
                    <span className={`ml-label ml-${mlPred.risk_label.toLowerCase()}`}>
                      {(mlPred.ml_flood_risk * 100).toFixed(0)}% {mlPred.risk_label}
                    </span>
                  </div>
                )}

                {node.is_isolated && (
                  <div className="popup-isolated">⚠️ ZONE ISOLATED — No passable route</div>
                )}
                {node.time_to_critical_h !== null && node.time_to_critical_h !== undefined && (
                  <div className="popup-row">
                    <span>Time to Critical</span>
                    <span>{node.time_to_critical_h}h</span>
                  </div>
                )}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
