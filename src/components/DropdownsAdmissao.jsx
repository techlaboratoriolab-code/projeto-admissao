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
  const [query, setQuery] = useState(value || '');
  const [aberto, setAberto] = useState(false);

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

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

  if (loading) {
    return (
      <input
        type="text"
        disabled
        className={className}
        value="Carregando convênios..."
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

  const encontrarConvenio = (nomeDigitado) => {
    const alvo = normalizar(nomeDigitado);
    if (!alvo) return null;
    return convenios.find((convenio) => normalizar(convenio?.nome) === alvo) || null;
  };

  const conveniosFiltrados = convenios
    .filter((convenio) => {
      const texto = normalizar(query);
      if (!texto) return true;
      const nome = normalizar(convenio?.nome);
      return nome.includes(texto);
    })
    .slice(0, 80);

  const selecionarConvenio = (convenio) => {
    const nome = convenio?.nome || '';
    setQuery(nome);
    onChange(convenio || null, nome);
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
          const convenioSelecionado = encontrarConvenio(nomeDigitado);
          onChange(convenioSelecionado, nomeDigitado);
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
        placeholder="Digite ou selecione um convênio..."
        autoComplete="off"
      />

      {aberto && !disabled && (
        <div className="mt-1 w-full max-h-64 overflow-y-auto rounded-md border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 shadow-lg">
          {conveniosFiltrados.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-neutral-400">
              Nenhum convênio encontrado
            </div>
          ) : (
            conveniosFiltrados.map((convenio) => (
              <button
                key={convenio.id}
                type="button"
                className="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-neutral-100 hover:bg-gray-100 dark:hover:bg-neutral-700"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selecionarConvenio(convenio)}
              >
                <div className="font-medium">{convenio.nome}</div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Dropdown para seleção de Fonte Pagadora (Instituição)
 */
export function FontePagadoraSelect({ value, onChange, disabled = false, className = "" }) {
  const [instituicoes, setInstituicoes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState(value || '');
  const [aberto, setAberto] = useState(false);

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

  useEffect(() => {
    setQuery(value || '');
  }, [value]);

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
      <input
        type="text"
        disabled
        className={className}
        value="Carregando fontes pagadoras..."
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

  const encontrarInstituicao = (nomeDigitado) => {
    const alvo = normalizar(nomeDigitado);
    if (!alvo) return null;
    return instituicoes.find((instituicao) => normalizar(instituicao?.nome) === alvo) || null;
  };

  const instituicoesFiltradas = instituicoes
    .filter((instituicao) => {
      const texto = normalizar(query);
      if (!texto) return true;
      const nome = normalizar(instituicao?.nome);
      return nome.includes(texto);
    })
    .slice(0, 80);

  const selecionarInstituicao = (instituicao) => {
    const nome = instituicao?.nome || '';
    setQuery(nome);
    onChange(instituicao || null, nome);
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
          const instituicaoSelecionada = encontrarInstituicao(nomeDigitado);
          onChange(instituicaoSelecionada, nomeDigitado);
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
        placeholder="Digite ou selecione uma fonte pagadora..."
        autoComplete="off"
      />

      {aberto && !disabled && (
        <div className="mt-1 w-full max-h-64 overflow-y-auto rounded-md border border-gray-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 shadow-lg">
          {instituicoesFiltradas.length === 0 ? (
            <div className="px-3 py-2 text-sm text-gray-500 dark:text-neutral-400">
              Nenhuma fonte pagadora encontrada
            </div>
          ) : (
            instituicoesFiltradas.map((instituicao) => (
              <button
                key={instituicao.id}
                type="button"
                className="w-full text-left px-3 py-2 text-sm text-gray-900 dark:text-neutral-100 hover:bg-gray-100 dark:hover:bg-neutral-700"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selecionarInstituicao(instituicao)}
              >
                <div className="font-medium">{instituicao.nome}</div>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

