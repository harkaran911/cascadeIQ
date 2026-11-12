import React from 'react';
import { approveDeployment } from '../../services/api';

function urgencyColor(score) {
  if (score >= 0.7) return '#f85149';
  if (score >= 0.4) return '#d29922';
  return '#3fb950';
}

export default function DirectivesPanel({ directives, onRefresh }) {
  const handleApprove = async (id) => {
    try {
      await approveDeployment(id);
      onRefresh();
    } catch (e) {
      console.error(e);
    }
  };

  const pending = directives.filter(d => d.status === 'recommended' || d.status === 'approved');

  return (
    <div>
      <div className="panel-section">
        <h3>Optimizer Directives</h3>
        {directives.length === 0 && (
          <p style={{ color: '#8b949e', fontSize: 12 }}>
            No directives yet — click "Run Optimizer" to generate deployment recommendations.
          </p>
        )}
      </div>

      {pending.map((d, i) => (
        <div key={d.id || i} className="card" style={{ borderLeft: `3px solid ${urgencyColor(d.urgency_score)}` }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: '#8b949e' }}>#{d.priority_rank + 1} — Resource #{d.resource_id}</span>
            <span style={{ fontSize: 11, color: urgencyColor(d.urgency_score), fontWeight: 700 }}>
              {(d.urgency_score * 100).toFixed(0)}% urgent
            </span>
          </div>

          <div style={{ margin: '6px 0', fontSize: 13 }}>
            Zone {d.from_zone_id} → <strong style={{ color: '#e6edf3' }}>{d.zone_name || `Zone ${d.to_zone_id}`}</strong>
          </div>

          {d.estimated_travel_min && (
            <div style={{ fontSize: 11, color: '#8b949e', marginBottom: 4 }}>
              🕐 {d.estimated_travel_min} min travel
              {d.deadline_minutes && ` · ⏰ Act within ${d.deadline_minutes} min`}
            </div>
          )}

          <p style={{ fontSize: 11, color: '#8b949e', fontStyle: 'italic', marginBottom: 8 }}>
            {d.rationale}
          </p>

          {d.status === 'recommended' && (
            <div style={{ display: 'flex', gap: 6 }}>
              <button className="primary" style={{ flex: 1, fontSize: 11 }} onClick={() => handleApprove(d.id)}>
                ✅ Approve
              </button>
              <button style={{ flex: 1, fontSize: 11 }}>✗ Dismiss</button>
            </div>
          )}
          {d.status === 'approved' && (
            <span style={{ fontSize: 11, color: '#39d353' }}>✓ Approved — In Progress</span>
          )}
        </div>
      ))}
    </div>
  );
}
