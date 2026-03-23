import React, { useState } from 'react';
import { ConvenioSelect, LocalOrigemSelect, FontePagadoraSelect, MedicoSelect } from './DropdownsAdmissao';

// Converte qualquer valor (objeto, array, primitivo) para string legível
const safeStr = (val) => {
  if (val == null) return '';
  if (typeof val === 'string') return val;
  if (typeof val === 'number') return String(val);
  if (Array.isArray(val)) return val.map(v => (typeof v === 'object' ? JSON.stringify(v) : v)).join(', ');
  if (typeof val === 'object') {
    // Endereço -> formato legível
    const { logradouro, numEndereco, bairro, cidade, uf, cep, complemento } = val;
    const parts = [logradouro, numEndereco, complemento, bairro, cidade, uf, cep].filter(Boolean);
    if (parts.length > 0) return parts.join(', ');
    return JSON.stringify(val);
  }
  return String(val);
};

const PatientCard = ({ patient, onPatientUpdate, onValidarCPF, validandoCPF = false }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState({});
  const [saveConfirmed, setSaveConfirmed] = useState(false);

  const handleEdit = () => {
    setEditedData({ ...patient });
    setSaveConfirmed(false);
    setIsEditing(true);
  };

  const handleSave = () => {
    if (onPatientUpdate) {
      onPatientUpdate(editedData);
    }
    setIsEditing(false);
    setSaveConfirmed(true);
    setTimeout(() => setSaveConfirmed(false), 3000);
  };

  const handleCancel = () => {
    setEditedData({});
    setIsEditing(false);
  };

  const handleChange = (field, value) => {
    setEditedData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="w-[380px] h-screen bg-white dark:bg-neutral-900 overflow-y-auto shadow-[-1px_0_0_rgba(0,0,0,0.06)] dark:shadow-[-1px_0_0_rgba(0,0,0,0.3)] sticky top-0 scrollbar-custom max-xl:w-[360px] max-lg:w-[320px] max-md:w-full max-md:h-auto max-md:max-h-[50vh] transition-colors flex flex-col" style={{ order: 2 }}>

      {/* Header do card */}
      <div className="px-5 py-4 border-b border-slate-100 dark:border-neutral-800 bg-gradient-to-r from-slate-50 to-white dark:from-neutral-900 dark:to-neutral-900 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400 dark:text-neutral-500 uppercase tracking-widest leading-none mb-0.5">Paciente</p>
              <h2 className="text-sm font-bold text-slate-800 dark:text-neutral-100 leading-none">Dados da Admissão</h2>
            </div>
          </div>
          {!isEditing ? (
            <button
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-300 border border-slate-200 dark:border-neutral-700 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-600 dark:hover:text-blue-400 hover:border-blue-200 dark:hover:border-blue-700"
              onClick={handleEdit}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Editar
            </button>
          ) : (
            <div className="flex gap-1.5">
              <button
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500 text-white border-0 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:bg-emerald-600"
                onClick={handleSave}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                Salvar
              </button>
              <button
                className="flex items-center gap-1 px-3 py-1.5 bg-slate-100 dark:bg-neutral-800 text-slate-600 dark:text-neutral-300 border border-slate-200 dark:border-neutral-700 rounded-lg text-xs font-semibold cursor-pointer transition-all hover:bg-slate-200"
                onClick={handleCancel}
              >
                Cancelar
              </button>
            </div>
          )}
        </div>

        {saveConfirmed && (
          <div className="mb-3 px-3 py-2 rounded-lg border border-emerald-200 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 text-xs font-semibold flex items-center gap-1.5">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            Dados salvos com sucesso
          </div>
        )}

        {/* Nome do paciente em destaque */}
        <div className="bg-slate-50 dark:bg-neutral-800 rounded-lg px-3.5 py-2.5 border border-slate-100 dark:border-neutral-700">
          <p className="text-[10px] font-semibold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-0.5">Nome Completo</p>
          <p className="text-sm font-bold text-slate-800 dark:text-neutral-100 leading-tight truncate">
            {safeStr(patient?.name) || <span className="text-slate-400 dark:text-neutral-500 font-normal italic">Não informado</span>}
          </p>
        </div>
      </div>

      {/* Corpo com dados */}
      <div className="flex-1 p-5 overflow-y-auto scrollbar-custom scrollbar-left">
      {/* Dados do Paciente */}
      <section className="mb-4">
        <p className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">Dados do Paciente</p>

        {/* ID do Paciente */}
        {patient?.idPaciente && (
          <div className="mb-3.5 p-2.5 bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 rounded">
            <label className="block text-[11px] font-medium text-blue-700 dark:text-blue-400 mb-1 uppercase tracking-wide">ID do Paciente</label>
            <p className="text-sm font-bold text-blue-900 dark:text-blue-300">{patient.idPaciente}</p>
          </div>
        )}

        <div className="mb-3.5">
          <label className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">
            Nome Completo
            <span className="text-red-500 font-bold">*</span>
          </label>
          {isEditing ? (
            <input
              type="text"
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.name || ''}
              onChange={(e) => handleChange('name', e.target.value)}
            />
          ) : (
            safeStr(patient?.name)
              ? <p className="text-sm font-semibold text-[#1a1a1a] dark:text-neutral-100">{safeStr(patient.name)}</p>
              : <p className="text-sm font-semibold text-red-500 dark:text-red-400 flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  Não informado — obrigatório
                </p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">
            Data de Nascimento
            <span className="text-red-500 font-bold">*</span>
          </label>
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
            safeStr(patient?.birthDate)
              ? <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient.birthDate)}</p>
              : <p className="text-sm font-semibold text-red-500 dark:text-red-400 flex items-center gap-1">
                  <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  Não informado — obrigatório
                </p>
          )}
        </div>

        <div className="mb-3.5">
          <label className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">
            Sexo
            <span className="text-red-500 font-bold">*</span>
          </label>
          {isEditing ? (
            <select
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
              value={editedData.gender || editedData.sexo || ''}
              onChange={(e) => setEditedData(prev => ({ ...prev, gender: e.target.value, sexo: e.target.value }))}
            >
              <option value="">Selecionar</option>
              <option value="M">Masculino</option>
              <option value="F">Feminino</option>
            </select>
          ) : (
            (() => {
              const sexoVal = patient?.gender || patient?.sexo || patient?.Sexo || patient?.DesSexo || '';
              const sexoLabel = sexoVal === 'M' || sexoVal === 'm' || /^masc/i.test(sexoVal) ? 'Masculino'
                              : sexoVal === 'F' || sexoVal === 'f' || /^fem/i.test(sexoVal) ? 'Feminino'
                              : sexoVal || null;
              return sexoLabel
                ? <p className="text-sm font-semibold text-[#333] dark:text-neutral-300">{sexoLabel}</p>
                : <p className="text-sm font-semibold text-red-500 dark:text-red-400 flex items-center gap-1">
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Não informado — obrigatório
                  </p>;
            })()
          )}
        </div>

        <div className="mb-3.5">
          <label className="block text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">Idade</label>
          <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.age) || 'Não informado'}</p>
        </div>

        <div className="mb-3.5">
          <label className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-neutral-400 mb-1 uppercase tracking-wide">
            CPF
            <span className="text-red-500 font-bold">*</span>
          </label>
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
              {safeStr(patient?.cpf)
                ? <p className="text-sm text-[#333] dark:text-neutral-300 mb-2">{safeStr(patient.cpf)}</p>
                : <p className="text-sm font-semibold text-red-500 dark:text-red-400 flex items-center gap-1 mb-2">
                    <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    Não informado — obrigatório
                  </p>
              }

              {/* 🆕 BOTÃO VALIDAR CPF */}
              {patient?.cpf && onValidarCPF && (
                <button
                  onClick={onValidarCPF}
                  disabled={validandoCPF}
                  className="w-full py-2.5 px-4 flex items-center justify-center gap-2 bg-gradient-to-br from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white text-sm font-semibold rounded-lg shadow-md shadow-emerald-500/30 hover:shadow-lg hover:shadow-emerald-500/40 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer border-0 disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                >
                  <span className="text-base leading-none">{validandoCPF ? '⏳' : '✓'}</span>
                  {validandoCPF ? 'Validando CPF...' : 'Validar na Receita Federal'}
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.rg) || 'Não informado'}</p>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.phone) || 'Não informado'}</p>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.email) || 'Não informado'}</p>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.insuranceCardNumber) || 'Não informado'}</p>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.numGuia) || 'Não informado'}</p>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.address) || 'Não informado'}</p>
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
            <p className="text-base leading-relaxed whitespace-pre-wrap dark:text-neutral-300">{safeStr(patient?.exams) || 'Não informado'}</p>
          )}
        </div>
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Requisição */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">Requisição</h2>
        {isEditing ? (
          <input
            type="text"
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
            value={editedData.recordNumber || ''}
            onChange={(e) => handleChange('recordNumber', e.target.value)}
            placeholder="Número da requisição"
          />
        ) : (
          <p className="text-2xl font-bold text-secondary dark:text-blue-400">{safeStr(patient?.recordNumber) || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Local de origem */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">Local de origem</h2>
        {isEditing ? (
          <LocalOrigemSelect
            value={editedData.origin || ''}
            onChange={(selectedOrigem) => handleChange('origin', selectedOrigem?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.origin) || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Fonte pagadora */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">Fonte pagadora</h2>
        {isEditing ? (
          <FontePagadoraSelect
            value={editedData.payingSource || ''}
            onChange={(selectedFonte) => handleChange('payingSource', selectedFonte?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.payingSource) || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Convênio */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">CONVÊNIO</h2>
        {isEditing ? (
          <ConvenioSelect
            value={editedData.insurance || ''}
            onChange={(selectedConvenio) => handleChange('insurance', selectedConvenio?.nome || '')}
            className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
          />
        ) : (
          <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.insurance) || 'Não informado'}</p>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Médico Solicitante */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">MÉDICO SOLICITANTE</h2>
        {isEditing ? (
          <>
            <MedicoSelect
              value={editedData.doctorName || ''}
              onChange={(selectedMedico, nomeDigitado) => {
                const nomeFinal = (nomeDigitado ?? selectedMedico?.nome ?? '').trim();
                const crmFinal = selectedMedico?.crm && selectedMedico?.uf
                  ? `CRM: ${selectedMedico.crm}/${selectedMedico.uf}`
                  : (editedData.doctorCRM || '');

                setEditedData(prev => ({
                  ...prev,
                  doctorName: nomeFinal,
                  doctorCRM: selectedMedico ? crmFinal : prev.doctorCRM,
                  idMedico: selectedMedico?.id ? selectedMedico.id.toString() : prev.idMedico
                }));
              }}
              className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md transition-all bg-neutral-50 dark:bg-neutral-700 dark:text-neutral-100 dark:placeholder:text-neutral-500 mb-2 focus:outline-none focus:border-primary focus:bg-white dark:focus:bg-neutral-600 focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
            />
            <div className="w-full px-3.5 py-2.5 text-sm border-2 border-neutral-200 dark:border-neutral-600 rounded-md bg-neutral-50 dark:bg-neutral-700 text-gray-700 dark:text-neutral-300">
              {safeStr(editedData.doctorCRM) || 'Não informado'}
            </div>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-[#1a1a1a] dark:text-neutral-100 mb-1">{safeStr(patient?.doctorName) || 'Não informado'}</p>
            <p className="text-xs text-gray-500 dark:text-neutral-400 uppercase tracking-wide">{safeStr(patient?.doctorCRM) || ''}</p>
          </>
        )}
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Atendimento */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">ATENDIMENTO</h2>
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
            <p className="text-sm text-[#333] dark:text-neutral-300">{safeStr(patient?.collectionDate) || 'Não informado'}</p>
          )}
        </div>
      </section>

      <div className="h-px bg-neutral-200 dark:bg-neutral-700 my-4"></div>

      {/* Status */}
      <section className="mb-4">
        <h2 className="text-[10px] font-bold text-slate-400 dark:text-neutral-500 uppercase tracking-widest mb-3">STATUS</h2>
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
            <span>{safeStr(patient?.statusText) || 'Pendente'}</span>
          </div>
        )}
      </section>
      </div>
    </div>
  );
};

export default PatientCard;
