import React, { useState } from 'react';

const PatientCard = ({ patient, onPatientUpdate }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({});

  const handleEdit = () => {
    setEditedData({ ...patient });
    setIsEditing(true);
  };

  const handleSave = () => {
    if (onPatientUpdate) {
      onPatientUpdate(editedData);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedData({});
    setIsEditing(false);
  };

  const handleChange = (field, value) => {
    setEditedData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="patient-card">
      {/* Logo LAB */}
      <div className="lab-logo">LAB</div>

      {/* Botão de edição */}
      <div className="card-actions">
        {!isEditing ? (
          <button className="btn-edit-card" onClick={handleEdit} title="Editar dados do paciente">
            Editar
          </button>
        ) : (
          <div className="edit-actions">
            <button className="btn-save-card" onClick={handleSave} title="Salvar alterações">
              Salvar
            </button>
            <button className="btn-cancel-card" onClick={handleCancel} title="Cancelar edição">
              Cancelar
            </button>
          </div>
        )}
      </div>

      {/* Dados do Paciente */}
      <section className="section">
        <h2 className="section-title">DADOS DO PACIENTE</h2>
        <div className="info-group">
          <label className="info-label">Nome Completo</label>
          {isEditing ? (
            <input
              type="text"
              className="info-input"
              value={editedData.name || ''}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          ) : (
            <p className="info-value name">{patient?.name || '{paciente.nome_completo}'}</p>
          )}
        </div>
        <div className="info-group">
          <label className="info-label">Data de Nascimento</label>
          {isEditing ? (
            <input
              type="date"
              className="info-input"
              value={editedData.birthDate ? editedData.birthDate.split('/').reverse().join('-') : ''}
              onChange={(e) => {
                const dataBr = e.target.value.split('-').reverse().join('/');
                handleChange('birthDate', dataBr);
              }}
            />
          ) : (
            <p className="info-value">{patient?.birthDate || '{paciente.data_nascimento}'}</p>
          )}
        </div>
        <div className="info-group">
          <label className="info-label">Idade</label>
          <p className="info-value">{patient?.age || '{paciente.idade}'}</p>
        </div>
        <div className="info-group">
          <label className="info-label">CPF</label>
          {isEditing ? (
            <input
              type="text"
              className="info-input"
              value={editedData.cpf || ''}
              onChange={(e) => handleChange('cpf', e.target.value)}
              placeholder="000.000.000-00"
            />
          ) : (
            <p className="info-value">{patient?.cpf || 'Não informado'}</p>
          )}
        </div>
        <div className="info-group">
          <label className="info-label">RG</label>
          {isEditing ? (
            <input
              type="text"
              className="info-input"
              value={editedData.rg || ''}
              onChange={(e) => handleChange('rg', e.target.value)}
            />
          ) : (
            <p className="info-value">{patient?.rg || 'Não informado'}</p>
          )}
        </div>
        <div className="info-group">
          <label className="info-label">Telefone</label>
          {isEditing ? (
            <input
              type="text"
              className="info-input"
              value={editedData.phone || ''}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="(00) 00000-0000"
            />
          ) : (
            <p className="info-value">{patient?.phone || 'Não informado'}</p>
          )}
        </div>
        <div className="info-group">
          <label className="info-label">Endereço</label>
          {isEditing ? (
            <textarea
              className="info-textarea"
              value={editedData.address || ''}
              onChange={(e) => handleChange('address', e.target.value)}
              rows="2"
            />
          ) : (
            <p className="info-value">{patient?.address || 'Não informado'}</p>
          )}
        </div>
      </section>

      <div className="divider"></div>

      {/* Requisição */}
      <section className="section">
        <h2 className="section-title">Requisição</h2>
        <p className="prontuario-number">{patient?.recordNumber || '{requisicao.numero}'}</p>
      </section>

      <div className="divider"></div>

      {/* Local de origem */}
      <section className="section">
        <h2 className="section-title">Local de origem</h2>
        <p className="info-value">{patient?.origin || '{requisicao.local_origem}'}</p>
      </section>

      <div className="divider"></div>

      {/* Fonte pagadora */}
      <section className="section">
        <h2 className="section-title">Fonte pagadora</h2>
        <p className="info-value">{patient?.payingSource || '{requisicao.fonte_pagadora}'}</p>
      </section>

      <div className="divider"></div>

      {/* Convênio */}
      <section className="section">
        <h2 className="section-title">CONVÊNIO</h2>
        <p className="info-value">{patient?.insurance || '{convenio.nome}'}</p>
      </section>

      <div className="divider"></div>

      {/* Médico Solicitante */}
      <section className="section">
        <h2 className="section-title">MÉDICO SOLICITANTE</h2>
        <p className="info-value doctor-name">{patient?.doctorName || '{medico.nome_completo}'}</p>
        <p className="info-crm">{patient?.doctorCRM || '{medico.crm}'}</p>
      </section>

      <div className="divider"></div>

      {/* Atendimento */}
      <section className="section">
        <h2 className="section-title">ATENDIMENTO</h2>
        <div className="info-group">
          <label className="info-label">Data da Coleta</label>
          <p className="info-value">{patient?.collectionDate || '{atendimento.data_coleta}'}</p>
        </div>
      </section>

      <div className="divider"></div>

      {/* Status */}
      <section className="section">
        <h2 className="section-title">STATUS</h2>
        <div className={`status-badge ${patient?.status || 'released'}`}>
          <span>{patient?.statusText || '{laudo.status}'}</span>
        </div>
      </section>
    </div>
  );
};

export default PatientCard;
