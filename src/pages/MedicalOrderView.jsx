import React, { useState } from 'react';
import PatientCard from '../components/PatientCard';
import DocumentViewer from '../components/DocumentViewer';

const MedicalOrderView = () => {
  const [patientData] = useState(null);

  const [medicalOrderImage, setMedicalOrderImage] = useState(null);

  return (
    <div className="flex w-full min-h-screen max-md:flex-col">
      <PatientCard patient={patientData} />
      <DocumentViewer
        documentType="medical-order"
        imageUrl={medicalOrderImage}
        placeholderText="Imagem do Pedido Médico&#10;&#10;Arraste sua imagem aqui ou&#10;substitua este placeholder"
      />
    </div>
  );
};

export default MedicalOrderView;
