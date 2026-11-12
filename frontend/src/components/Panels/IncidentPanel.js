import React, { useState, useEffect } from 'react';
import { fetchIncidents } from '../../services/api';

function severityBadge(s) {
  if (s >= 0.75) return 'critical';
  if (s >= 0.5)  return 'high';
  if (s >= 0.3)  return 'moderate';
  return 'low';
}

const SOURCE_ICONS = {
  authority: '🏛️',
  imd: '🌦️',
  citizen: '👤',
  satellite: '🛰️',
  social: '📱',
};

const TYPE_ICONS = {
  flood: '🌊',
  road_blocked: '🚧',
  bridge_failure: '🌉',
  power_outage: '⚡',
  trapped_people: '🆘',
  medical_emergency: '🏥',
  infrastructure_damage: '🏗️',
};

export default function IncidentPanel({ selectedZone }) {
  const [incidents, setIncidents] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchIncidents().then(setIncidents).catch(console.error);
    const t = setInterval(() => fetchIncidents().then(setIncidents).catch(console.error), 15000);
    return () => clearInterval(t);
  }, []);

  const filtered = filter === 'all'
    ? incidents
    : incidents.filter(i => i.zone_id === selectedZone?.id);

  return (
    <div>
      <div className="panel-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <h3>Incident Feed</h3>
          <span style={{ fontSize: 12, color: '#8b949e' }}>{filtered.length} reports</span>
        </div>
        <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
          <button style={{ fontSize: 11, padding: '3px 8px' }}
            className={filter === 'all' ? 'primary' : ''}
            onClick={() => setFilter('all')}>All</button>
          {selectedZone && (
            <button style={{ fontSize: 11, padding: '3px 8px' }}
              className={filter === 'zone' ? 'primary' : ''}
              onClick={() => setFilter('zone')}>
              {selectedZone.name}
            </button>
          )}
        </div>
      </div>

      {filtered.length === 0 && (
        <p style={{ color: '#8b949e', fontSize: 12 }}>No incidents reported yet.</p>
      )}

      {filtered.map(inc => {
        // AI suggested a different type with high confidence?
        const aiDiffers = inc.ai_incident_type &&
          inc.ai_incident_type !== inc.incident_type &&
          inc.ai_confidence >= 0.75;

        return (
          <div key={inc.id} className="card" style={{ borderLeft: `3px solid ${borderColor(inc.severity)}` }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span style={{ fontSize: 13 }}>
                {TYPE_ICONS[inc.incident_type] || '⚠️'} {formatType(inc.incident_type)}
              </span>
              <span className={`badge badge-${severityBadge(inc.severity)}`}>
                {severityBadge(inc.severity)}
              </span>
            </div>
            <p style={{ marginTop: 4 }}>{inc.description || 'No description'}</p>

            {/* AI classification tag */}
            {inc.ai_incident_type && inc.ai_confidence >= 0.65 && (
              <div style={{ marginTop: 5, fontSize: 10, display: 'flex', gap: 6, alignItems: 'center' }}>
                <span style={{
                  background: '#388bfd18', border: '1px solid #388bfd55',
                  borderRadius: 4, padding: '1px 6px', color: '#388bfd',
                }}>
                  🤖 AI: {formatType(inc.ai_incident_type)} · {(inc.ai_confidence * 100).toFixed(0)}%
                </span>
                {aiDiffers && (
                  <span style={{ color: '#d29922', fontSize: 10 }}>⚠ disagrees with reported type</span>
                )}
              </div>
            )}
            {inc.ai_reasoning && (
              <p style={{ fontSize: 10, color: '#8b949e', marginTop: 3, fontStyle: 'italic' }}>
                {inc.ai_reasoning}
              </p>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 6, fontSize: 11, color: '#8b949e' }}>
              <span>{SOURCE_ICONS[inc.source]} {inc.source}</span>
              <span>Trust: {(inc.trust_weight * 100).toFixed(0)}%</span>
              {inc.corroboration_count > 1 && (
                <span style={{ color: '#39d353' }}>✓ {inc.corroboration_count}x</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function borderColor(severity) {
  if (severity >= 0.75) return '#ff0000';
  if (severity >= 0.5)  return '#f85149';
  if (severity >= 0.3)  return '#d29922';
  return '#3fb950';
}

function formatType(t) {
  return t?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || t;
}
