import React, { useState } from 'react';
import PatientCard from '../components/PatientCard';
import DocumentViewer from '../components/DocumentViewer';

const ExamResultView = () => {
  const [patientData] = useState(null);

  const [examResultImage, setExamResultImage] = useState(null);

  return (
    <div className="medical-system-layout">
      <PatientCard patient={patientData} />
      <DocumentViewer
        documentType="exam-result"
        imageUrl={examResultImage}
        placeholderText="Imagem do Resultado&#10;&#10;Arraste sua imagem aqui"
      />
    </div>
  );
};

export default ExamResultView;
