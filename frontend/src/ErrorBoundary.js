import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('CascadeIQ crash:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', height: '100vh', background: '#0d1117',
          color: '#e6edf3', fontFamily: 'monospace', padding: 32,
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚡</div>
          <h2 style={{ color: '#f85149', marginBottom: 8 }}>CascadeIQ encountered an error</h2>
          <p style={{ color: '#8b949e', marginBottom: 24, textAlign: 'center', maxWidth: 480 }}>
            The dashboard failed to render. This is usually a temporary API connectivity issue.
          </p>
          <pre style={{
            background: '#161b22', border: '1px solid #30363d', borderRadius: 8,
            padding: 16, fontSize: 11, color: '#f85149', maxWidth: 600,
            overflow: 'auto', marginBottom: 24, whiteSpace: 'pre-wrap',
          }}>
            {this.state.error?.message || 'Unknown error'}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: '#388bfd', color: '#fff', border: 'none', borderRadius: 6,
              padding: '10px 24px', cursor: 'pointer', fontSize: 14, fontWeight: 600,
            }}
          >
            🔄 Reload Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
