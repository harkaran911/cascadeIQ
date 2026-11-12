import React from 'react';

function Metric({ label, value, color }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3, color: '#8b949e' }}>
        <span>{label}</span>
        <span style={{ color: color || '#e6edf3', fontWeight: 600 }}>{value}</span>
      </div>
    </div>
  );
}

function RiskBar({ value, color }) {
  return (
    <div style={{ height: 4, background: '#30363d', borderRadius: 2, marginTop: 3, marginBottom: 10 }}>
      <div style={{ width: `${value * 100}%`, height: '100%', background: color, borderRadius: 2, transition: 'width 0.5s' }} />
    </div>
  );
}

export default function StatusBar({ zone, zones, mlPredictions = {} }) {
  const criticalZones = zones ? zones.filter(z => z.severity_score >= 0.75) : [];
  const isolatedZones = zones ? zones.filter(z => z.is_isolated) : [];
  const highConf = zones ? zones.filter(z => z.incident_confidence >= 0.6) : [];

  return (
    <div style={{ padding: 12 }}>
      {/* Fleet overview */}
      <div className="panel-section">
        <h3>System Overview</h3>
        <Metric label="Total Zones" value={zones?.length || 0} />
        <Metric label="Critical Zones" value={criticalZones.length} color={criticalZones.length > 0 ? '#f85149' : '#3fb950'} />
        <Metric label="Isolated Zones" value={isolatedZones.length} color={isolatedZones.length > 0 ? '#d29922' : '#3fb950'} />
        <Metric label="High Confidence ICS" value={highConf.length} color={highConf.length > 0 ? '#388bfd' : '#8b949e'} />
      </div>

      {/* Selected zone detail */}
      {zone ? (
        <div className="panel-section">
          <h3>Selected Zone</h3>
          <div className="card">
            <h4 style={{ marginBottom: 4 }}>{zone.name}</h4>
            <p style={{ marginBottom: 8 }}>{zone.district} District</p>

            <div style={{ fontSize: 12 }}>
              <div style={{ marginBottom: 4, color: '#8b949e' }}>Severity</div>
              <RiskBar value={zone.severity_score} color={getSevColor(zone.severity_score)} />

              <div style={{ marginBottom: 4, color: '#8b949e' }}>ICS Confidence</div>
              <RiskBar value={zone.incident_confidence} color="#388bfd" />

              <div style={{ marginBottom: 4, color: '#8b949e' }}>Vulnerability</div>
              <RiskBar value={zone.vulnerability_index} color="#d29922" />

              {/* ML Flood Risk — hidden when model hasn't loaded yet */}
              {mlPredictions[zone.id] && (() => {
                const ml = mlPredictions[zone.id];
                const mlColor = { CRITICAL: '#ff0000', HIGH: '#f85149', MODERATE: '#d29922', LOW: '#3fb950' }[ml.risk_label] || '#8b949e';
                return (
                  <>
                    <div style={{ marginBottom: 4, marginTop: 2, color: '#8b949e', display: 'flex', justifyContent: 'space-between' }}>
                      <span>🤖 ML Flood Risk</span>
                      <span style={{ color: mlColor, fontWeight: 700, fontSize: 11 }}>
                        {ml.risk_label} ({(ml.ml_flood_risk * 100).toFixed(0)}%)
                      </span>
                    </div>
                    <RiskBar value={ml.ml_flood_risk} color={mlColor} />
                  </>
                );
              })()}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 8, fontSize: 11 }}>
              <StatPill label="Population" value={zone.population?.toLocaleString()} />
              <StatPill label="Flood Depth" value={`${zone.flood_depth_m || 0}m`} />
              <StatPill label="Hospital" value={zone.has_hospital ? '✅' : '❌'} />
              <StatPill label="Shelter" value={zone.has_shelter ? '✅' : '❌'} />
            </div>

            {zone.is_isolated && (
              <div style={{ marginTop: 10, padding: '6px 10px', background: '#f8514915', border: '1px solid #f85149', borderRadius: 6, fontSize: 11, color: '#f85149' }}>
                ⚠️ ISOLATED — All road links degraded or flooded. Aerial/boat access only.
              </div>
            )}

            {zone.time_to_critical_h !== null && zone.time_to_critical_h !== undefined && zone.time_to_critical_h > 0 && (
              <div style={{ marginTop: 8, fontSize: 11, color: '#d29922' }}>
                ⏳ Estimated {zone.time_to_critical_h}h before critical threshold
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="panel-section">
          <p style={{ color: '#8b949e', fontSize: 12 }}>Click a zone on the map to see details.</p>
        </div>
      )}

      {/* Critical zone list */}
      {criticalZones.length > 0 && (
        <div className="panel-section">
          <h3>Critical Zones</h3>
          {criticalZones.map(z => (
            <div key={z.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: '1px solid #30363d', fontSize: 12 }}>
              <span>{z.name}</span>
              <span style={{ color: '#f85149', fontWeight: 700 }}>{(z.severity_score * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatPill({ label, value }) {
  return (
    <div style={{ background: '#0d1117', border: '1px solid #30363d', borderRadius: 4, padding: '4px 8px' }}>
      <div style={{ color: '#8b949e', fontSize: 10 }}>{label}</div>
      <div style={{ fontWeight: 600 }}>{value}</div>
    </div>
  );
}

function getSevColor(s) {
  if (s >= 0.75) return '#ff0000';
  if (s >= 0.5)  return '#f85149';
  if (s >= 0.3)  return '#d29922';
  return '#3fb950';
}
