import React, { useState } from 'react';
import { submitIncident } from '../../services/api';

const INCIDENT_TYPES = [
  { value: 'flood', label: '🌊 Flood' },
  { value: 'road_blocked', label: '🚧 Road Blocked' },
  { value: 'bridge_failure', label: '🌉 Bridge Failure' },
  { value: 'trapped_people', label: '🆘 Trapped People' },
  { value: 'medical_emergency', label: '🏥 Medical Emergency' },
  { value: 'power_outage', label: '⚡ Power Outage' },
  { value: 'infrastructure_damage', label: '🏗️ Infrastructure Damage' },
];

export default function ReportForm({ zones, onSubmit }) {
  const [form, setForm] = useState({
    zone_id: '',
    incident_type: 'flood',
    severity: 0.6,
    description: '',
    reporter_name: '',
    reporter_contact: '',
    source: 'citizen',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [aiResult, setAiResult] = useState(null);

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async e => {
    e.preventDefault();
    if (!form.zone_id) return;
    setSubmitting(true);
    setAiResult(null);
    try {
      const res = await submitIncident({ ...form, zone_id: parseInt(form.zone_id), severity: parseFloat(form.severity) });
      setSuccess(true);
      if (res?.ai_classification) setAiResult(res.ai_classification);
      setTimeout(() => { setSuccess(false); setAiResult(null); }, 8000);
      onSubmit();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="panel-section">
        <h3>📡 Report Incident</h3>
        <p style={{ color: '#8b949e', fontSize: 11, marginBottom: 12 }}>
          Your report is trust-weighted by MSEFE and fused with satellite + authority data.
        </p>
      </div>

      <div className="form-group">
        <label>Zone *</label>
        <select name="zone_id" value={form.zone_id} onChange={handleChange} required>
          <option value="">Select a zone…</option>
          {zones.map(z => (
            <option key={z.id} value={z.id}>{z.name} — {z.district}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Incident Type *</label>
        <select name="incident_type" value={form.incident_type} onChange={handleChange}>
          {INCIDENT_TYPES.map(t => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Severity — {Math.round(form.severity * 100)}%</label>
        <input type="range" name="severity" min="0.1" max="1.0" step="0.05"
          value={form.severity} onChange={handleChange}
          style={{ width: '100%', accentColor: '#388bfd' }} />
      </div>

      <div className="form-group">
        <label>Description</label>
        <textarea name="description" value={form.description} onChange={handleChange}
          rows={3} placeholder="Describe what you're seeing…" />
      </div>

      <div className="form-group">
        <label>Your Name</label>
        <input name="reporter_name" value={form.reporter_name} onChange={handleChange}
          placeholder="Optional" />
      </div>

      <div className="form-group">
        <label>Contact</label>
        <input name="reporter_contact" value={form.reporter_contact} onChange={handleChange}
          placeholder="Phone / email (optional)" />
      </div>

      <button type="submit" className="primary" style={{ width: '100%' }} disabled={submitting || !form.zone_id}>
        {submitting ? '⏳ Submitting…' : '📤 Submit Report'}
      </button>

      {success && (
        <div style={{ marginTop: 10, padding: 8, background: '#3fb95020', border: '1px solid #3fb950', borderRadius: 6, fontSize: 12, color: '#3fb950', textAlign: 'center' }}>
          ✅ Report received — MSEFE updating confidence scores
        </div>
      )}

      {/* AI classification result — shown for 8s after submit */}
      {aiResult && (
        <div style={{ marginTop: 8, padding: 10, background: '#388bfd12', border: '1px solid #388bfd44', borderRadius: 6, fontSize: 12 }}>
          <div style={{ color: '#388bfd', fontWeight: 700, marginBottom: 4 }}>
            🤖 AI Classification Result
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ color: '#e6edf3' }}>
              {aiResult.incident_type?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown'}
            </span>
            <span style={{ color: '#8b949e' }}>
              {(aiResult.confidence * 100).toFixed(0)}% confident
            </span>
          </div>
          {aiResult.keywords?.length > 0 && (
            <div style={{ marginBottom: 4 }}>
              {aiResult.keywords.map(k => (
                <span key={k} style={{ background: '#388bfd22', borderRadius: 3, padding: '1px 5px', marginRight: 4, fontSize: 11, color: '#58a6ff' }}>
                  {k}
                </span>
              ))}
            </div>
          )}
          {aiResult.reasoning && (
            <p style={{ color: '#8b949e', fontSize: 11, fontStyle: 'italic', margin: 0 }}>
              {aiResult.reasoning}
            </p>
          )}
        </div>
      )}
    </form>
  );
}
