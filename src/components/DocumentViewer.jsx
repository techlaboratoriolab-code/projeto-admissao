import React from 'react';

const DocumentViewer = ({ documentType, imageUrl, placeholderText }) => {
  const getDocumentBadge = () => {
    switch (documentType) {
      case 'medical-order':
        return {
          label: '📋 Pedido Médico',
          className: 'bg-secondary/10 text-secondary'
        };
      case 'report':
        return {
          label: '📄 Laudo',
          className: 'bg-success/10 text-success-dark'
        };
      case 'exam-result':
        return {
          label: '🔬 Resultado Exame',
          className: 'bg-purple-100 text-purple-800'
        };
      default:
        return {
          label: '📋 Documento',
          className: 'bg-gray-100 text-gray-600'
        };
    }
  };

  const badge = getDocumentBadge();

  return (
    <div className="flex-1 p-6 bg-neutral-50">
      {/* Header */}
      <header className="flex items-center justify-between bg-white px-4.5 py-[18px] rounded-lg shadow-card mb-4">
        <h1 className="text-[17px] font-bold text-[#333] m-0">DOCUMENTOS E EXAMES</h1>
        <div className={`px-3.5 py-1.5 rounded-[5px] text-xs font-semibold ${badge.className}`}>
          <span>{badge.label}</span>
        </div>
      </header>

      {/* Imagem do Documento */}
      <div className="bg-white rounded-xl shadow-[0_4px_16px_rgba(0,0,0,0.08)] p-10 h-[calc(100vh-170px)] flex items-center justify-center">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={badge.label}
            className="max-w-full max-h-full object-contain rounded-lg"
          />
        ) : (
          <div className="w-full h-full bg-gray-100 rounded-lg flex items-center justify-center">
            <p className="text-lg font-normal text-gray-400 text-center whitespace-pre-line leading-relaxed max-sm:text-sm">
              {placeholderText || 'Imagem do Documento\n\nArraste sua imagem aqui ou\nsubstitua este placeholder'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentViewer;
