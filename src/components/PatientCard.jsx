import React, { useState } from 'react';
import { ConvenioSelect, LocalOrigemSelect, FontePagadoraSelect } from './DropdownsAdmissao';

const PatientCard = ({ patient, onPatientUpdate, onValidarCPF }) => {
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
    <div className="w-[420px] h-screen bg-white dark:bg-neutral-800 p-6 overflow-y-auto shadow-[2px_0_12px_rgba(0,0,0,0.08)] dark:shadow-[2px_0_12px_rgba(0,0,0,0.3)] sticky top-0 scrollbar-custom max-xl:w-[400px] max-lg:w-[350px] max-md:w-full max-md:h-auto max-md:max-h-[50vh] max-md:p-5 transition-colors">
      {/* Título do sistema */}
      <h2 className="text-xl font-bold text-gray-900 dark:text-neutral-100 mb-4">
        Sistema de Admissão
      </h2>
      
      {/* Botão de edição */}
      <div className="mb-5">
        {!isEditing ? (
          <button
            className="px-5 py-2.5 bg-blue-500 text-white border-0 rounded-md text-sm font-semibold cursor-pointer transition-colors hover:bg-blue-600"
            onClick={handleEdit}
            title="Editar dados do paciente"
          >
            Editar
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              className="px-5 py-2.5 bg-success text-white border-0 rounded-md text-sm font-semibold cursor-pointer transition-colors hover:bg-success-dark"
              onClick={handleSave}
              title="Salvar alterações"
            >
              Salvar
            </button>
            <button
              className="px-5 py-2.5 bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 border-0 rounded-md text-sm font-semibold cursor-pointer transition-colors hover:bg-neutral-300 dark:hover:bg-neutral-600"
              onClick={handleCancel}
              title="Cancelar edição"
            >
              Cancelar
            </button>
          </div>
        )}
      </div>

      {/* Dados do Paciente */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">DADOS DO PACIENTE</h2>

        {/* ID do Paciente */}
        {patient?.idPaciente && (
          <div className="mb-3.5 p-2.5 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded">
            <label className="block text-[11px] font-medium text-blue-700 dark:text-blue-400 mb-1 uppercase tracking-wide">ID do Paciente</label>
            <p className="text-sm font-bold text-blue-900 dark:text-blue-300">{patient.idPaciente}</p>
          </div>
        )}

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Nome Completo</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.name || ''}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          ) : (
            <p className="text-sm font-semibold text-[#1a1a1a] dark:text-neutral-100">{patient?.name || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Data de Nascimento</label>
          {isEditing ? (
            <input
              type="date"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.birthDate ? editedData.birthDate.split('/').reverse().join('-') : ''}
              onChange={(e) => {
                const dataBr = e.target.value.split('-').reverse().join('/');
                handleChange('birthDate', dataBr);
              }}
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.birthDate || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Idade</label>
          <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.age || 'Não informado'}</p>
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">CPF</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.cpf || ''}
              onChange={(e) => handleChange('cpf', e.target.value)}
              placeholder="000.000.000-00"
            />
          ) : (
            <div>
              <p className="text-sm text-[#333] dark:text-neutral-300 mb-2">{patient?.cpf || 'Não informado'}</p>

              {/* 🆕 BOTÃO VALIDAR CPF */}
              {patient?.cpf && onValidarCPF && (
                <button
                  onClick={onValidarCPF}
                  className="w-full py-2.5 px-4 text-white font-semibold text-sm rounded-lg transition-all duration-300 hover:-translate-y-0.5"
                  style={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
                    border: 'none',
                    cursor: 'pointer'
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.boxShadow = '0 6px 16px rgba(16, 185, 129, 0.4)';
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.3)';
                  }}
                >
                  <span style={{ fontSize: '16px', marginRight: '6px' }}>✓</span>
                  Validar na Receita Federal
                </button>
              )}
            </div>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">RG</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.rg || ''}
              onChange={(e) => handleChange('rg', e.target.value)}
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.rg || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Telefone</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.phone || ''}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="(00) 00000-0000"
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.phone || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">E-mail</label>
          {isEditing ? (
            <input
              type="email"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.email || ''}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="email@exemplo.com"
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.email || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Nº Carteirinha</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.insuranceCardNumber || ''}
              onChange={(e) => handleChange('insuranceCardNumber', e.target.value)}
              placeholder="000000000000000"
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.insuranceCardNumber || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Nº Guia Convênio</label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.numGuia || ''}
              onChange={(e) => handleChange('numGuia', e.target.value)}
              placeholder="Número da guia"
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.numGuia || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Endereço</label>
          {isEditing ? (
            <textarea
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 resize-y min-h-[60px] focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.address || ''}
              onChange={(e) => handleChange('address', e.target.value)}
              rows="2"
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.address || 'Não informado'}</p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-sm font-semibold text-[#1e40af] dark:text-blue-400 mb-1">Exames</label>
          {isEditing ? (
            <textarea
              className="w-full px-3 py-3 text-base border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 resize-y min-h-[120px] leading-relaxed focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.exams || ''}
              onChange={(e) => handleChange('exams', e.target.value)}
              rows="6"
              placeholder="Digite os nomes dos exames separados por vírgula"
            />
          ) : (
            <p className="text-base leading-relaxed whitespace-pre-wrap dark:text-neutral-300">{patient?.exams || 'Não informado'}</p>
          )}
        </div>
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Requisição */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">Requisição</h2>
        {isEditing ? (
          <input
            type="text"
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
            value={editedData.recordNumber || ''}
            onChange={(e) => handleChange('recordNumber', e.target.value)}
            placeholder="Número da requisição"
          />
        ) : (
          <p className="text-2xl font-bold text-secondary dark:text-blue-400">{patient?.recordNumber || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Local de origem */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">Local de origem</h2>
        {isEditing ? (
          <LocalOrigemSelect
            value={editedData.origin || ''}
            onChange={(selectedOrigem) => handleChange('origin', selectedOrigem?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.origin || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Fonte pagadora */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">Fonte pagadora</h2>
        {isEditing ? (
          <FontePagadoraSelect
            value={editedData.payingSource || ''}
            onChange={(selectedFonte) => handleChange('payingSource', selectedFonte?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.payingSource || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Convênio */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">CONVÊNIO</h2>
        {isEditing ? (
          <ConvenioSelect
            value={editedData.insurance || ''}
            onChange={(selectedConvenio) => handleChange('insurance', selectedConvenio?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.insurance || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Médico Solicitante */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">MÉDICO SOLICITANTE</h2>
        {isEditing ? (
          <>
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 mb-2 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.doctorName || ''}
              onChange={(e) => handleChange('doctorName', e.target.value)}
              placeholder="Nome do médico"
            />
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.doctorCRM || ''}
              onChange={(e) => handleChange('doctorCRM', e.target.value)}
              placeholder="CRM do médico"
            />
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-[#1a1a1a] dark:text-neutral-100 mb-1">{patient?.doctorName || 'Não informado'}</p>
            <p className="text-xs text-gray-500 dark:text-neutral-400 uppercase tracking-wide">{patient?.doctorCRM || ''}</p>
          </>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Atendimento */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">ATENDIMENTO</h2>
        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Data da Coleta</label>
          {isEditing ? (
            <input
              type="date"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.collectionDate ? editedData.collectionDate.split('/').reverse().join('-') : ''}
              onChange={(e) => {
                const dataBr = e.target.value.split('-').reverse().join('/');
                handleChange('collectionDate', dataBr);
              }}
            />
          ) : (
            <p className="text-sm text-[#333] dark:text-neutral-300">{patient?.collectionDate || 'Não informado'}</p>
          )}
        </div>
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Status */}
      <section className="mb-4">
        <h2 className="text-base font-bold text-[#333] dark:text-neutral-100 mb-3.5">STATUS</h2>
        {isEditing ? (
          <select
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
            value={editedData.status || ''}
            onChange={(e) => handleChange('status', e.target.value)}
          >
            <option value="">Selecionar</option>
            <option value="released">Liberado</option>
            <option value="pending">Pendente</option>
            <option value="rejected">Rejeitado</option>
            <option value="cancelled">Cancelado</option>
          </select>
        ) : (
          <div className={`inline-flex items-center justify-center px-4 py-1.5 rounded-md text-xs font-semibold ${
            patient?.status === 'released' ? 'bg-success-light text-success-dark' :
            patient?.status === 'pending' ? 'bg-yellow-100 text-warning' :
            patient?.status === 'processing' ? 'bg-blue-100 text-blue-600' :
            'bg-gray-100 text-gray-600'
          }`}>
            <span>{patient?.statusText || 'Pendente'}</span>
          </div>
        )}
      </section>
    </div>
  );
};

export default PatientCard;
