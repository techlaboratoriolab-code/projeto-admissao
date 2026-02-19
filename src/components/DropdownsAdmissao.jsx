import { useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

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
        const response = await axios.get(`${API_BASE_URL}/api/convenios`);
        
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
        const response = await axios.get(`${API_BASE_URL}/api/fontes-pagadoras`);
        
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
        const response = await axios.get(`${API_BASE_URL}/api/locais-origem`);
        
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
