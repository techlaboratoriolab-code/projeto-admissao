import React, { useState } from 'react';
import PatientCard from '../components/PatientCard';
import DocumentViewer from '../components/DocumentViewer';

const ReportView = () => {
  const [patientData] = useState(null);

  const [reportImage, setReportImage] = useState(null);

  return (
    <div className="medical-system-layout">
      <PatientCard patient={patientData} />
      <DocumentViewer
        documentType="report"
        imageUrl={reportImage}
        placeholderText="Imagem do Laudo&#10;&#10;Arraste sua imagem aqui"
      />
    </div>
  );
};

export default ReportView;
