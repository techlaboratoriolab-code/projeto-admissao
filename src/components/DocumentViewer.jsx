import React from 'react';

const DocumentViewer = ({ documentType, imageUrl, placeholderText }) => {
  const getDocumentBadge = () => {
    switch (documentType) {
      case 'medical-order':
        return {
          label: '📋 Pedido Médico',
          className: 'badge-medical-order'
        };
      case 'report':
        return {
          label: '📄 Laudo',
          className: 'badge-report'
        };
      case 'exam-result':
        return {
          label: '🔬 Resultado Exame',
          className: 'badge-exam'
        };
      default:
        return {
          label: '📋 Documento',
          className: 'badge-default'
        };
    }
  };

  const badge = getDocumentBadge();

  return (
    <div className="document-viewer">
      {/* Header */}
      <header className="document-header">
        <h1 className="document-title">DOCUMENTOS E EXAMES</h1>
        <div className={`document-badge ${badge.className}`}>
          <span>{badge.label}</span>
        </div>
      </header>

      {/* Imagem do Documento */}
      <div className="document-container">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={badge.label}
            className="document-image"
          />
        ) : (
          <div className="document-placeholder">
            <p className="placeholder-text">
              {placeholderText || 'Imagem do Documento\n\nArraste sua imagem aqui ou\nsubstitua este placeholder'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;
