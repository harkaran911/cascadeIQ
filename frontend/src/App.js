import React, { useState, useEffect, useCallback } from 'react';
import CascadeMap from './components/Map/CascadeMap';
import IncidentPanel from './components/Panels/IncidentPanel';
import DirectivesPanel from './components/Panels/DirectivesPanel';
import StatusBar from './components/Panels/StatusBar';
import ReportForm from './components/Panels/ReportForm';
import { fetchZones, fetchCascade, fetchDirectives, fetchWeather, fetchMlPredictions, runOptimizer } from './services/api';
import './App.css';

export default function App() {
  const [zones, setZones] = useState([]);
  const [cascade, setCascade] = useState(null);
  const [directives, setDirectives] = useState([]);
  const [weather, setWeather] = useState(null);
  const [mlPredictions, setMlPredictions] = useState({});  // {zone_id: prediction_obj}
  const [selectedZone, setSelectedZone] = useState(null);
  const [activePanel, setActivePanel] = useState('incidents'); // 'incidents' | 'directives' | 'report'
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [z, c, d, w] = await Promise.all([
        fetchZones(),
        fetchCascade(),
        fetchDirectives(),
        fetchWeather(),
      ]);
      setZones(z);
      setCascade(c);
      setDirectives(d);
      setWeather(w);
      setLastUpdate(new Date());

      // ML predictions run separately — don't block main refresh if model unavailable
      try {
        const mlData = await fetchMlPredictions();
        // Convert array → {zone_id: prediction} map for O(1) lookup
        const mlMap = {};
        (mlData.predictions || []).forEach(p => { mlMap[p.zone_id] = p; });
        setMlPredictions(mlMap);
      } catch (mlErr) {
        // Model not loaded yet or backend restarting — silent degradation
        console.warn('ML predictions unavailable:', mlErr?.message);
      }
    } catch (e) {
      console.error('Refresh error:', e);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 30000); // auto-refresh every 30s
    return () => clearInterval(interval);
  }, [refresh]);

  const handleRunOptimizer = async () => {
    setLoading(true);
    try {
      await runOptimizer();
      await refresh();
    } finally {
      setLoading(false);
    }
  };

  const criticalCount = zones.filter(z => z.severity_score >= 0.75).length;
  const isolatedCount = zones.filter(z => z.is_isolated).length;

  return (
    <div className="app-shell">
      {/* ── Top bar ─────────────────────────────────────── */}
      <header className="topbar">
        <div className="topbar-brand">
          <span className="brand-icon">⚡</span>
          <span className="brand-name">CascadeIQ</span>
          <span className="brand-sub">Punjab / Sutlej Basin — Live Flood Command</span>
        </div>
        <div className="topbar-stats">
          {criticalCount > 0 && (
            <span className="stat-chip critical">🔴 {criticalCount} Critical</span>
          )}
          {isolatedCount > 0 && (
            <span className="stat-chip isolated">🚫 {isolatedCount} Isolated</span>
          )}
          {weather && (
            <span className="stat-chip weather">
              🌧 {weather.rain_1h_mm} mm/h — {weather.location}
            </span>
          )}
          {lastUpdate && (
            <span className="stat-chip muted">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
        </div>
        <div className="topbar-actions">
          <button className="primary" onClick={handleRunOptimizer} disabled={loading}>
            {loading ? '⚙️ Optimizing…' : '🎯 Run Optimizer'}
          </button>
          <button onClick={refresh}>🔄 Refresh</button>
        </div>
      </header>

      {/* ── Main layout ─────────────────────────────────── */}
      <div className="main-layout">
        {/* Left sidebar */}
        <aside className="sidebar-left">
          <nav className="panel-tabs">
            {[
              { id: 'incidents', label: '📋 Incidents' },
              { id: 'directives', label: '🎯 Directives' },
              { id: 'report', label: '📡 Report' },
            ].map(tab => (
              <button
                key={tab.id}
                className={`tab-btn ${activePanel === tab.id ? 'active' : ''}`}
                onClick={() => setActivePanel(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="panel-body">
            {activePanel === 'incidents' && (
              <IncidentPanel selectedZone={selectedZone} />
            )}
            {activePanel === 'directives' && (
              <DirectivesPanel directives={directives} onRefresh={refresh} />
            )}
            {activePanel === 'report' && (
              <ReportForm zones={zones} onSubmit={refresh} />
            )}
          </div>
        </aside>

        {/* Map */}
        <main className="map-container">
          {cascade ? (
            <CascadeMap
              cascade={cascade}
              zones={zones}
              onZoneClick={setSelectedZone}
              selectedZone={selectedZone}
              mlPredictions={mlPredictions}
            />
          ) : (
            <div className="loading-screen">
              <div className="spinner" />
              <p>Loading disaster graph…</p>
            </div>
          )}
        </main>

        {/* Right sidebar — selected zone detail */}
        <aside className="sidebar-right">
          <StatusBar zone={selectedZone} zones={zones} mlPredictions={mlPredictions} />
        </aside>
      </div>
    </div>
  );
}
