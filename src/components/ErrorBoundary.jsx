import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Erro capturado:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          padding: '40px',
          background: '#f8f9fa',
          fontFamily: 'Inter, sans-serif'
        }}>
          <div style={{
            maxWidth: '700px',
            width: '100%',
            background: 'white',
            borderRadius: '12px',
            padding: '32px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.1)',
            border: '2px solid #ef4444'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
              <span style={{ fontSize: '32px' }}>⚠️</span>
              <div>
                <h2 style={{ margin: 0, color: '#dc2626', fontSize: '20px', fontWeight: '700' }}>
                  Erro na Aplicação
                </h2>
                <p style={{ margin: '4px 0 0 0', color: '#6b7280', fontSize: '14px' }}>
                  Ocorreu um erro inesperado ao renderizar esta página
                </p>
              </div>
            </div>

            <div style={{
              background: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '20px'
            }}>
              <p style={{ margin: '0 0 8px 0', fontWeight: '600', color: '#991b1b', fontSize: '14px' }}>
                Mensagem do erro:
              </p>
              <code style={{
                display: 'block',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: '#dc2626',
                fontSize: '13px',
                background: '#fff',
                padding: '10px',
                borderRadius: '6px',
                border: '1px solid #fca5a5'
              }}>
                {this.state.error?.toString() || 'Erro desconhecido'}
              </code>
            </div>

            {this.state.errorInfo?.componentStack && (
              <details style={{ marginBottom: '20px' }}>
                <summary style={{
                  cursor: 'pointer',
                  color: '#6b7280',
                  fontSize: '13px',
                  fontWeight: '600',
                  userSelect: 'none',
                  marginBottom: '8px'
                }}>
                  🔍 Ver detalhes técnicos (stack trace)
                </summary>
                <pre style={{
                  background: '#1f2937',
                  color: '#e5e7eb',
                  padding: '16px',
                  borderRadius: '8px',
                  fontSize: '11px',
                  overflow: 'auto',
                  maxHeight: '300px',
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace'
                }}>
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={this.handleReload}
                style={{
                  padding: '10px 24px',
                  background: '#3b82f6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                🔄 Tentar Novamente
              </button>
              <button
                onClick={() => window.location.reload()}
                style={{
                  padding: '10px 24px',
                  background: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
              >
                🔁 Recarregar Página
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
