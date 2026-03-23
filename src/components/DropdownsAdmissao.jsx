import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

const ngrokHeaders = { 'ngrok-skip-browser-warning': 'true' };

/**
 * Dropdown pesquisável para seleção de Médico (permite digitação manual)
 */
export function MedicoSelect({ value, onChange, disabled = false, className = "" }) {
  const [medicos, setMedicos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState(value || '');
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    const carregarMedicos = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE_URL}/api/medicos`, { headers: ngrokHeaders });

        if (response.data.sucesso === 1) {
          const medicosOrdenados = (response.data.medicos || []).sort((a, b) =>
            (a.nome || '').localeCompare(b.nome || '', 'pt-BR')
          );
          setMedicos(medicosOrdenados);
        } else {
          setError('Erro ao carregar médicos');
        }
      } catch (err) {
        console.error('[MedicoSelect] Erro ao carregar médicos:', err);
        setError('Erro ao conectar com o servidor');
      } finally {
        setLoading(false);
      }
    };

    carregarMedicos();
  }, []);

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  if (loading) {
    return (
      <input
        type="text"
        disabled
        className={className}
        value="Carregando médicos..."
        readOnly
      />
    );
  }

  if (error) {
    return (
      <input
        type="text"
        disabled
        className={className}
        value={error}
        readOnly
      />
    );
  }

  const normalizar = (texto) => String(texto || '').trim().toLowerCase();

  const encontrarMedico = (nomeDigitado) => {
    const alvo = normalizar(nomeDigitado);
    if (!alvo) return null;
    return medicos.find((medico) => normalizar(medico?.nome) === alvo) || null;
  };

  const medicosFiltrados = medicos
    .filter((medico) => {
      const texto = normalizar(query);
      if (!texto) return true;
      const nome = normalizar(medico?.nome);
      const crmUf = normalizar(`${medico?.crm || ''}/${medico?.uf || ''}`);
      return nome.includes(texto) || crmUf.includes(texto);
    })
    .slice(0, 80);

  const selecionarMedico = (medico) => {
    const nome = medico?.nome || '';
    setQuery(nome);
    onChange(medico || null, nome);
    setAberto(false);
  };

  return (
    <div className="relative">
      <input
        type="text"
        value={query || ''}
        onChange={(e) => {
          const nomeDigitado = e.target.value;
          setQuery(nomeDigitado);
          setAberto(true);
          const medicoSelecionado = encontrarMedico(nomeDigitado);
          onChange(medicoSelecionado, nomeDigitado);
        }}
        onFocus={() => setAberto(true)}
        onClick={() => setAberto(true)}
        onKeyDown={(e) => {
          if (e.key === 'Escape') {
            setAberto(false);
          }
        }}
        disabled={disabled}
        className={className}
        placeholder="Digite ou selecione um médico..."
        autoComplete="off"
      />

      {aberto && !disabled && (
        <div className="mt-1 w-full max-h-64 overflow-y-auto rounded-md border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 shadow-lg">
          {medicosFiltrados.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-neutral-400">
              Nenhum médico encontrado
            </div>
          ) : (
            medicosFiltrados.map((medico) => (
              <button
                key={medico.id}
                type="button"
                className="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-neutral-100 hover:bg-gray-100 dark:hover:bg-neutral-700"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selecionarMedico(medico)}
              >
                <div className="font-medium">{medico.nome}</div>
                <div className="text-xs text-gray-500 dark:text-neutral-400">CRM {medico.crm}/{medico.uf}</div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Dropdown para seleção de Convênio
 */
export function ConvenioSelect({ value, onChange, disabled = false, className = "" }) {
  const [convenios, setConvenios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const carregarConvenios = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE_URL}/api/convenios`, { headers: ngrokHeaders });
        
        if (response.data.sucesso === 1) {
          const conveniosOrdenados = response.data.convenios.sort((a, b) => 
            a.nome.localeCompare(b.nome, 'pt-BR')
          );
          setConvenios(conveniosOrdenados);
        } else {
          setError('Erro ao carregar convênios');
        }
      } catch (err) {
        console.error('[ConvenioSelect] Erro ao carregar convênios:', err);
        setError('Erro ao conectar com o servidor');
      } finally {
        setLoading(false);
      }
    };

    carregarConvenios();
  }, []);

  if (loading) {
    return (
      <select disabled className={className}>
        <option>Carregando convênios...</option>
      </select>
    );
  }

  if (error) {
    return (
      <select disabled className={className}>
        <option>{error}</option>
      </select>
    );
  }

  // Encontrar o ID baseado no nome do valor
  const getValueForSelect = () => {
    if (!value) return '';
    const convenio = convenios.find(c => c.nome === value);
    return convenio?.id || '';
  };

  return (
    <select
      value={getValueForSelect()}
      onChange={(e) => {
        const convenioSelecionado = convenios.find(c => c.id.toString() === e.target.value);
        onChange(convenioSelecionado || null);
      }}
      disabled={disabled}
      className={className}
    >
      <option value="">Selecione um convênio...</option>
      {convenios.map((convenio) => (
        <option key={convenio.id} value={convenio.id}>
          {convenio.nome}
        </option>
      ))}
    </select>
  );
}

/**
 * Dropdown para seleção de Fonte Pagadora (Instituição)
 */
export function FontePagadoraSelect({ value, onChange, disabled = false, className = "" }) {
  const [instituicoes, setInstituicoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const carregarInstituicoes = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE_URL}/api/fontes-pagadoras`, { headers: ngrokHeaders });

        if (response.data.sucesso === 1) {
          const instituicoesOrdenadas = response.data.fontes.sort((a, b) =>
            a.nome.localeCompare(b.nome, 'pt-BR')
          );
          setInstituicoes(instituicoesOrdenadas);
        } else {
          setError('Erro ao carregar fontes pagadoras');
        }
      } catch (err) {
        console.error('[FontePagadoraSelect] Erro ao carregar instituições:', err);
        setError('Erro ao conectar com o servidor');
      } finally {
        setLoading(false);
      }
    };

    carregarInstituicoes();
  }, []);

  // Auto-selecionar "Particular" quando não há valor definido
  useEffect(() => {
    if (!loading && !error && instituicoes.length > 0 && (!value || value === 'Não informado') && onChange) {
      const particular = instituicoes.find(i => i.nome.toUpperCase().includes('PARTICULAR'));
      if (particular) {
        onChange(particular);
      }
    }
  }, [loading, instituicoes]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading) {
    return (
      <select disabled className={className}>
        <option>Carregando fontes pagadoras...</option>
      </select>
    );
  }

  if (error) {
    return (
      <select disabled className={className}>
        <option>{error}</option>
      </select>
    );
  }

  // Encontrar o ID baseado no nome do valor
  const getValueForSelect = () => {
    if (!value) return '';
    const instituicao = instituicoes.find(i => i.nome === value);
    return instituicao?.id || '';
  };

  return (
    <select
      value={getValueForSelect()}
      onChange={(e) => {
        const instituicaoSelecionada = instituicoes.find(i => i.id.toString() === e.target.value);
        onChange(instituicaoSelecionada || null);
      }}
      disabled={disabled}
      className={className}
    >
      <option value="">Selecione uma fonte pagadora...</option>
      {instituicoes.map((inst) => (
        <option key={inst.id} value={inst.id}>
          {inst.nome}
        </option>
      ))}
    </select>
  );
}

/**
 * Dropdown para seleção de Local de Origem
 */
export function LocalOrigemSelect({ value, onChange, disabled = false, className = "" }) {
  const [locais, setLocais] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const carregarLocais = async () => {
      try {
        setLoading(true);
        const response = await axios.get(`${API_BASE_URL}/api/locais-origem`, { headers: ngrokHeaders });
        
        if (response.data.sucesso === 1) {
          const locaisOrdenados = response.data.locais.sort((a, b) => 
            a.nome.localeCompare(b.nome, 'pt-BR')
          );
          setLocais(locaisOrdenados);
        } else {
          setError('Erro ao carregar locais de origem');
        }
      } catch (err) {
        console.error('[LocalOrigemSelect] Erro ao carregar locais:', err);
        setError('Erro ao conectar com o servidor');
      } finally {
        setLoading(false);
      }
    };

    carregarLocais();
  }, []);

  if (loading) {
    return (
      <select disabled className={className}>
        <option>Carregando locais de origem...</option>
      </select>
    );
  }

  if (error) {
    return (
      <select disabled className={className}>
        <option>{error}</option>
      </select>
    );
  }

  // Encontrar o ID baseado no nome do valor
  const getValueForSelect = () => {
    if (!value) return '';
    const local = locais.find(l => l.nome === value);
    return local?.id || '';
  };

  return (
    <select
      value={getValueForSelect()}
      onChange={(e) => {
        const localSelecionado = locais.find(l => l.id.toString() === e.target.value);
        onChange(localSelecionado || null);
      }}
      disabled={disabled}
      className={className}
    >
      <option value="">Selecione um local de origem...</option>
      {locais.map((local) => (
        <option key={local.id} value={local.id}>
          {local.nome}
        </option>
      ))}
    </select>
  );
}
