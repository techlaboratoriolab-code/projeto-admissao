import React, { useState, useEffect, useRef } from 'react';
import PatientCard from '../components/PatientCard';
import { API_BASE_URL, apiFetch } from '../config';
import { useAuth } from '../contexts/AuthContext';
import { ConvenioSelect, FontePagadoraSelect, LocalOrigemSelect } from '../components/DropdownsAdmissao';
import { useFilaCompartilhada } from '../hooks/useFilaCompartilhada';
import { supabase as supabaseClient } from '../lib/supabase';

const AdmissionView = () => {
  const { usuario } = useAuth();
  const [loading, setLoading] = useState(false);
  const [loadingRequisicao, setLoadingRequisicao] = useState(false);
  const [loadingOCR, setLoadingOCR] = useState(false);
  const [message, setMessage] = useState(null);
  const [imagens, setImagens] = useState([]);
  const [imagemSelecionada, setImagemSelecionada] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [dadosOCRConsolidados, setDadosOCRConsolidados] = useState([]);
  const [resultadoConsolidadoFinal, setResultadoConsolidadoFinal] = useState(null);
  const [imagensProcessadas, setImagensProcessadas] = useState(new Set());

  const [formData, setFormData] = useState({
    codRequisicao: '',
    idLaboratorio: '1',
    idUnidade: '1',
    idPaciente: '',
    dtaColeta: new Date().toISOString().split('T')[0],
    idConvenio: '',
    idLocalOrigem: '1',
    idFontePagadora: '',
    idMedico: '',
    idExame: '',
    examesConvenio: '',
    numGuia: '',
    matConvenio: '',
    fontePagadora: '',
    dadosClinicos: ''
  });

  const [patientData, setPatientData] = useState(null);
  const [requisicaoData, setRequisicaoData] = useState(null);
  const [sincronizacaoInfo, setSincronizacaoInfo] = useState(null);
  const [receitaFederalStatus, setReceitaFederalStatus] = useState(null); // 🆕 Status da validação da Receita Federal

  // 🆕 Estados para histórico de requisições do Supabase
  const [mostrarHistorico, setMostrarHistorico] = useState(false);
  const [requisicoesHistorico, setRequisicoesHistorico] = useState([]);
  const [loadingHistorico, setLoadingHistorico] = useState(false);
  const [buscaHistorico, setBuscaHistorico] = useState('');
  const [abaPrincipal, setAbaPrincipal] = useState('admissao'); // 'admissao' ou 'visualizar'

  // 🆕 Estados para edição de dados do paciente no modal
  const [modoEdicaoModal, setModoEdicaoModal] = useState(false);
  const [dadosEditaveis, setDadosEditaveis] = useState(null);
  const [dadosRequisicaoEditaveis, setDadosRequisicaoEditaveis] = useState(null);
  const [salvandoDados, setSalvandoDados] = useState(false);

  // Ref para debounce da busca automática
  const debounceRef = useRef(null);

  // Fila compartilhada multi-usuário (Supabase Realtime)
  const {
    filaRequisicoes, filaStatus, sessaoAtiva, euSouProcessador,
    iniciarSessao, atualizarItem, atualizarSessao,
    adquirirLockRevisao, liberarLockRevisao, aprovarItem: aprovarItemSupabase, pularItem: pularItemSupabase,
    resetarSessao: resetarSessaoHook
  } = useFilaCompartilhada();

  const [filaIndice, setFilaIndice] = useState(0); // local: índice sendo processado pelo OCR
  const [filaRevisaoIndice, setFilaRevisaoIndice] = useState(-1); // local: índice selecionado para revisão
  const [filaLog, setFilaLog] = useState([]);
  const autoStopRef = useRef(false);

  // Função para converter data DD/MM/YYYY para YYYY-MM-DD
  const converterDataParaISO = (data) => {
    if (!data) return '';

    // Converter para string se não for
    const dataStr = String(data).trim();

    // Se já está em formato ISO (YYYY-MM-DD), retorna
    if (/^\d{4}-\d{2}-\d{2}/.test(dataStr)) {
      return dataStr.split('T')[0]; // Remove hora se tiver
    }

    // Se está em formato DD/MM/YYYY
    if (/^\d{2}\/\d{2}\/\d{4}/.test(dataStr)) {
      const partes = dataStr.split('/');
      const dia = partes[0];
      const mes = partes[1];
      const ano = partes[2].split(' ')[0]; // Remove hora se tiver
      return `${ano}-${mes}-${dia}`;
    }

    return dataStr;
  };

  // Buscar dados da requisição quando código é alterado
  const buscarRequisicao = async (codRequisicao) => {
    if (!codRequisicao || codRequisicao.length < 10) return;

    setLoadingRequisicao(true);
    setMessage(null);

    // LIMPAR ESTADOS ANTERIORES (evitar herança entre requisições no modo automático)
    setResultadoConsolidadoFinal(null);
    setDadosOCRConsolidados([]);
    setImagensProcessadas(new Set());
    setReceitaFederalStatus(null);
    setPatientData(null);
    setRequisicaoData(null);
    setImagens([]);

    try {
      const response = await apiFetch(`${API_BASE_URL}/api/requisicao/${codRequisicao}`);
      const data = await response.json();

      if (response.ok) {
        // Atualizar dados do paciente para exibir no card lateral
        if (data.paciente) {
          // 🔍 DEBUG: Ver o que está vindo do backend
          console.log('[DEBUG] ===== DADOS COMPLETOS DO BACKEND =====');
          console.log('[DEBUG] data.paciente.dtaNasc:', data.paciente.dtaNasc);
          console.log('[DEBUG] tipo:', typeof data.paciente.dtaNasc);
          console.log('[DEBUG] data completo:', JSON.stringify(data, null, 2));
          console.log('[DEBUG] localOrigem:', data.localOrigem);
          console.log('[DEBUG] localOrigem.nome:', data.localOrigem?.nome);
          console.log('[DEBUG] fontePagadora:', data.fontePagadora);
          console.log('[DEBUG] fontePagadora.nome:', data.fontePagadora?.nome);
          console.log('[DEBUG] convenio:', data.convenio);
          console.log('[DEBUG] convenio.nome:', data.convenio?.nome);
          console.log('[DEBUG] =========================================');

          const idade = calcularIdade(data.paciente.dtaNasc);

          // 🆕 VERIFICAR VALIDAÇÃO DA RECEITA FEDERAL
          if (data.validacao_cpf) {
            if (data.validacao_cpf.fonte_dados !== 'receita_federal') {
              // Receita Federal não disponível ou falhou
              setReceitaFederalStatus({
                tipo: 'erro',
                mensagem: 'Validação da Receita Federal não disponível',
                detalhes: 'Os dados do paciente não foram validados pela Receita Federal. Verifique manualmente.'
              });
              setMessage({
                type: 'warning',
                text: '⚠️ Validação da Receita Federal não disponível. Verifique os dados do paciente manualmente.'
              });
            } else if (data.validacao_cpf.dados_corrigidos) {
              // Dados foram corrigidos pela Receita Federal
              setReceitaFederalStatus({
                tipo: 'sucesso',
                mensagem: 'Dados validados e corrigidos pela Receita Federal',
                detalhes: 'Os dados do paciente foram validados e corrigidos automaticamente.',
                comparacao: data.validacao_cpf.comparacao  // Adicionar dados comparativos
              });
              setMessage({
                type: 'info',
                text: '✓ Dados do paciente foram validados e corrigidos pela Receita Federal.'
              });
            } else if (data.validacao_cpf.fonte_dados === 'receita_federal') {
              // Dados validados e OK
              setReceitaFederalStatus({
                tipo: 'sucesso',
                mensagem: 'Dados validados pela Receita Federal',
                detalhes: 'Os dados do paciente foram validados e estão corretos.',
                comparacao: data.validacao_cpf.comparacao  // Adicionar dados comparativos
              });
            }
          } else {
            // Nenhuma informação de validação
            setReceitaFederalStatus({
              tipo: 'aviso',
              mensagem: 'Validação da Receita Federal não realizada',
              detalhes: 'A validação com a Receita Federal não foi executada.'
            });
          }

          setPatientData({
            idPaciente: data.paciente.idPaciente || data.paciente.CodPaciente || '',
            name: data.paciente.nome,
            age: `${idade} anos`,
            birthDate: formatarData(data.paciente.dtaNasc),
            recordNumber: data.requisicao.codRequisicao,
            origin: data.localOrigem?.nome || 'Não informado',
            payingSource: data.fontePagadora?.nome || 'Particular',
            insurance: data.convenio?.nome || 'Não informado',
            doctorName: data.medico?.nome || 'Não informado',
            doctorCRM: data.medico?.crm ? `CRM: ${data.medico.crm}/${data.medico.uf}` : 'Não informado',
            collectionDate: formatarData(data.requisicao.dtaColeta),
            statusText: 'Em andamento',
            status: 'in-progress',
            cpf: data.paciente.cpf,
            rg: data.paciente.rg,
            phone: data.paciente.telCelular,
            email: data.paciente.email,
            insuranceCardNumber: data.paciente.matriculaConvenio,
            numGuia: data.paciente.numGuia || data.requisicao?.numGuia || data.dados_primarios?.numGuia || 'Não informado',
            address: formatarEndereco(data.paciente.endereco),
            exams: data.requisicao?.examesNomes || 'Não informado'
          });
        }

        // Preencher formulário com dados da requisição - SEMPRE preencher da API
        setFormData(prev => {
          // Converter data para formato YYYY-MM-DD se necessário
          let dataColeta = data.requisicao.dtaColeta || prev.dtaColeta;
          if (dataColeta && dataColeta.includes('T')) {
            // Se vier com hora (2026-01-06T00:00:00), pegar só a data
            dataColeta = dataColeta.split('T')[0];
          }
          // Converter para ISO se estiver em formato DD/MM/YYYY
          dataColeta = converterDataParaISO(dataColeta);

          return {
            ...prev,
            codRequisicao: data.requisicao.codRequisicao,
            dtaColeta: dataColeta,
            // Aceitar tanto idPaciente quanto CodPaciente - NÃO usar prev.idPaciente para evitar herdar de requisição anterior
            idPaciente: (data.paciente.idPaciente || data.paciente.CodPaciente)?.toString() || '',
            // Buscar IDs tanto do objeto requisicao quanto dos objetos específicos - NÃO usar prev para evitar herdar de requisição anterior
            idConvenio: data.requisicao.idConvenio?.toString() || data.convenio?.id?.toString() || '',
            idLocalOrigem: data.requisicao.idLocalOrigem?.toString() || data.localOrigem?.id?.toString() || '1',
            idFontePagadora: data.requisicao.idFontePagadora?.toString() || data.fontePagadora?.id?.toString() || '',
            idMedico: data.requisicao.idMedico?.toString() || '',
            numGuia: data.requisicao.numGuia || '',
            dadosClinicos: data.requisicao.dadosClinicos || ''
            // examesConvenio e idExame serão preenchidos pelo OCR depois
          };
        });

        // 🆕 SE idPaciente está vazio MAS tem CPF, buscar automaticamente pelo CPF
        const idPacientePreenchido = data.paciente?.idPaciente || data.paciente?.CodPaciente;
        const cpfDisponivel = data.paciente?.cpf;

        console.log('[BUSCAR] 🔍 Iniciando verificação de paciente...');
        console.log('[BUSCAR]   idPaciente do OCR:', idPacientePreenchido || 'NÃO ENCONTRADO');
        console.log('[BUSCAR]   CPF do OCR:', cpfDisponivel || 'NÃO ENCONTRADO');

        if (!idPacientePreenchido && cpfDisponivel) {
          console.log('[BUSCAR] ⚠️ idPaciente vazio mas CPF disponível. Buscando automaticamente...');
          console.log('[BUSCAR]   CPF para busca:', cpfDisponivel);
          console.log('[BUSCAR]   URL da API:', `${API_BASE_URL}/api/paciente/buscar-por-cpf`);

          try {
            const responseCPF = await apiFetch(`${API_BASE_URL}/api/paciente/buscar-por-cpf`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ cpf: cpfDisponivel })
            });

            console.log('[BUSCAR] 📡 Status da requisição:', responseCPF.status);

            const resultCPF = await responseCPF.json();
            console.log('[BUSCAR] 📦 Resposta completa do backend:', resultCPF);

            if (resultCPF.sucesso && resultCPF.paciente?.idPaciente) {
              console.log('[BUSCAR] ✅ Paciente encontrado pelo CPF!');
              console.log('[BUSCAR]   ID:', resultCPF.paciente.idPaciente);
              console.log('[BUSCAR]   Nome:', resultCPF.paciente.nome);
              console.log('[BUSCAR]   Data Nascimento:', resultCPF.paciente.dataNascimento);

              // 🆕 LOG DE MÚLTIPLOS REGISTROS
              if (resultCPF.multiplos_registros) {
                console.warn('[BUSCAR] ⚠️ ATENÇÃO: Múltiplos registros encontrados!');
                console.warn('[BUSCAR]   Total de registros:', resultCPF.registros_encontrados);
                console.warn('[BUSCAR]   Registro selecionado (mais completo): ID', resultCPF.paciente.idPaciente);

                setMessage({
                  type: 'warning',
                  text: `⚠️ ATENÇÃO: ${resultCPF.registros_encontrados} registros encontrados com este CPF. Usando o mais completo (ID: ${resultCPF.paciente.idPaciente})`
                });
              }

              // Atualizar formData com o idPaciente encontrado
              setFormData(prev => ({
                ...prev,
                idPaciente: resultCPF.paciente.idPaciente.toString()
              }));

              // Atualizar patientData para exibir no PatientCard
              setPatientData(prev => ({
                ...prev,
                idPaciente: resultCPF.paciente.idPaciente.toString()
              }));

              console.log('[BUSCAR] ✅ idPaciente preenchido automaticamente no formData e patientData:', resultCPF.paciente.idPaciente);
            } else {
              console.warn('[BUSCAR] ⚠️ Paciente não encontrado pelo CPF no sistema');
              console.warn('[BUSCAR]   Sucesso:', resultCPF.sucesso);
              console.warn('[BUSCAR]   Erro:', resultCPF.erro);

              setMessage({
                type: 'warning',
                text: `⚠️ CPF ${cpfDisponivel} não encontrado no sistema. Será necessário cadastrar o paciente.`
              });
            }
          } catch (error) {
            console.error('[BUSCAR] ❌ Erro ao buscar paciente pelo CPF:', error);
            console.error('[BUSCAR]   Tipo do erro:', error.name);
            console.error('[BUSCAR]   Mensagem:', error.message);
            console.error('[BUSCAR]   Stack:', error.stack);

            setMessage({
              type: 'error',
              text: `❌ Erro ao buscar paciente pelo CPF: ${error.message}`
            });
          }
        } else if (idPacientePreenchido) {
          console.log('[BUSCAR] ✅ idPaciente já preenchido pelo OCR:', idPacientePreenchido);
        } else {
          console.warn('[BUSCAR] ⚠️ Nem idPaciente nem CPF disponíveis no OCR!');
          console.warn('[BUSCAR]   Será necessário buscar ou cadastrar paciente manualmente');

          setMessage({
            type: 'error',
            text: '⚠️ OCR não conseguiu extrair CPF do documento. Busque ou cadastre o paciente manualmente.'
          });
        }

        // Armazenar dados completos da requisição
        setRequisicaoData(data);

        // Verificar se houve sincronização 0085 <-> 0200
        if (data.sincronizacao && data.sincronizacao.sincronizado) {
          setSincronizacaoInfo({
            sincronizado: true,
            codigoCorrespondente: data.sincronizacao.codigo_correspondente,
            tipo: data.sincronizacao.tipo_sincronizacao,
            camposSincronizados: data.sincronizacao.campos_sincronizados
          });
        } else {
          setSincronizacaoInfo(null);
        }

        // SEMPRE gerar JSON em topografia logo após carregar os dados
        console.log('[TOPOGRAFIA] Gerando visualização em topografia dos dados carregados');
        // ⚠️ IMPORTANTE: Passar dados como parâmetro, pois setRequisicaoData é assíncrono
        setTimeout(() => {
          consolidarResultados(null, data);
        }, 500);

        // Armazenar imagens
        if (data.imagens && data.imagens.length > 0) {
          setImagens(data.imagens);
          setMessage({
            type: 'success',
            text: `Requisição encontrada! ${data.imagens.length} imagens carregadas. Dados em topografia gerados.`
          });
        } else {
          setImagens([]);
          setMessage({
            type: 'success',
            text: 'Requisição encontrada! Nenhuma imagem disponível. Dados em topografia gerados.'
          });
        }
      } else {
        setMessage({
          type: 'error',
          text: data.erro || 'Requisição não encontrada'
        });
        setPatientData(null);
        setImagens([]);
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Erro ao buscar requisição: ${error.message}`
      });
      setPatientData(null);
      setImagens([]);
    } finally {
      setLoadingRequisicao(false);
    }
  };

  // BUSCA AUTOMÁTICA DESABILITADA - usar botão "Iniciar Análise Automática"
  // useEffect(() => {
  //   const timer = setTimeout(() => {
  //     if (formData.codRequisicao) {
  //       buscarRequisicao(formData.codRequisicao);
  //     }
  //   }, 800);
  //   return () => clearTimeout(timer);
  // }, [formData.codRequisicao]);

  // OCR AUTOMÁTICO DESABILITADO - usar botão "Iniciar Análise Automática"
  // useEffect(() => {
  //   if (imagens.length > 0) {
  //     console.log(`Processando OCR automaticamente para ${imagens.length} imagens...`);
  //     const imagensValidas = imagens;
  //     console.log(`${imagensValidas.length} arquivos para processar OCR (incluindo PDFs)`);
  //     imagensValidas.forEach((img, index) => {
  //       setTimeout(() => {
  //         if (!imagensProcessadas.has(img.nome)) {
  //           console.log(`Auto-processando imagem ${index + 1}/${imagensValidas.length}: ${img.nome}`);
  //           processarOCR(img.url, img.nome, true);
  //         }
  //       }, index * 3000);
  //     });
  //   }
  // }, [imagens]);

  // CONSOLIDAÇÃO AUTOMÁTICA DESABILITADA - usar botão "Iniciar Análise Automática"
  // useEffect(() => {
  //   if (imagens.length > 0 && dadosOCRConsolidados.length === imagens.length && requisicaoData) {
  //     console.log('[CONSOLIDAR] Todas as imagens processadas, consolidando resultados...');
  //     consolidarResultados();
  //   }
  // }, [dadosOCRConsolidados.length, imagens.length]);

  // Função para preencher formulário com dados do OCR
  const preencherFormularioComOCR = async (resultadoConsolidado) => {
    console.log('[PREENCHER] 🚀 FUNÇÃO CHAMADA!');
    console.log('[PREENCHER] 📦 Argumento recebido (resultadoConsolidado):', resultadoConsolidado);
    console.log('[PREENCHER] 📦 Tipo:', typeof resultadoConsolidado);
    console.log('[PREENCHER] 📦 É null?', resultadoConsolidado === null);
    console.log('[PREENCHER] 📦 É undefined?', resultadoConsolidado === undefined);

    if (!resultadoConsolidado || !resultadoConsolidado.requisicoes || resultadoConsolidado.requisicoes.length === 0) {
      console.log('[PREENCHER] ❌ Nenhum dado para preencher');
      console.log('[PREENCHER] - resultadoConsolidado existe?', !!resultadoConsolidado);
      console.log('[PREENCHER] - requisicoes existe?', !!resultadoConsolidado?.requisicoes);
      console.log('[PREENCHER] - requisicoes.length:', resultadoConsolidado?.requisicoes?.length);
      return;
    }

    const req = resultadoConsolidado.requisicoes[0];
    let camposPreenchidos = [];

    console.log('[PREENCHER] ✓ Iniciando preenchimento automático do formulário...');
    console.log('[PREENCHER] Dados OCR recebidos:', JSON.stringify(req, null, 2));
    console.log('[PREENCHER] FormData atual:', formData);

    // Criar objeto de atualização APENAS com campos do OCR
    const atualizacoesOCR = {};

    // Código da requisição do OCR (se não estiver preenchido)
    if (req.comentarios_gerais?.requisicao_entrada && !formData.codRequisicao) {
      atualizacoesOCR.codRequisicao = req.comentarios_gerais.requisicao_entrada;
      camposPreenchidos.push('Código da Requisição (OCR)');
      console.log('[PREENCHER] ✓ :', req.comentarios_gerais.requisicao_entrada);
    }

    // Data de coleta do OCR (sobrescreve API se existir)
    if (req.requisicao?.dtaColeta?.valor) {
      const dataConvertida = converterDataParaISO(req.requisicao.dtaColeta.valor);
      atualizacoesOCR.dtaColeta = dataConvertida;
      camposPreenchidos.push('Data de Coleta (OCR)');
      console.log('[PREENCHER] ✓ Data de coleta:', req.requisicao.dtaColeta.valor, '→', dataConvertida);
    } else if (!formData.dtaColeta) {
      // Fallback: usar data atual se não tiver data no OCR nem no formulário
      const dataAtual = new Date().toISOString().split('T')[0];
      atualizacoesOCR.dtaColeta = dataAtual;
      camposPreenchidos.push('Data de Coleta (Atual)');
      console.log('[PREENCHER] ✓ Data de coleta (fallback):', dataAtual);
    }

    // Dados clínicos
    if (req.requisicao?.dadosClinicos?.valor) {
      atualizacoesOCR.dadosClinicos = req.requisicao.dadosClinicos.valor;
      camposPreenchidos.push('Dados Clínicos');
      console.log('[PREENCHER] ✓ Dados clínicos:', req.requisicao.dadosClinicos.valor);
    }

    // Número da guia
    if (req.convenio?.numGuia?.valor) {
      atualizacoesOCR.numGuia = req.convenio.numGuia.valor;
      camposPreenchidos.push('Número da Guia');
      console.log('[PREENCHER] ✓ Número da guia:', req.convenio.numGuia.valor);
    }

    // Convênio - matricula do convênio
    if (req.convenio?.matConvenio?.valor) {
      atualizacoesOCR.matConvenio = req.convenio.matConvenio.valor;
      camposPreenchidos.push('Matrícula do Convênio');
      console.log('[PREENCHER] ✓ Matrícula do convênio:', req.convenio.matConvenio.valor);
    }

    // ✅ CONVÊNIO - Nome do plano de saúde (CORRIGIDO: usar nomeConvenio)
    if (req.convenio?.nomeConvenio?.valor) {
      atualizacoesOCR.insurance = req.convenio.nomeConvenio.valor;
      camposPreenchidos.push('Convênio (OCR)');
      console.log('[PREENCHER] ✅ Convênio extraído:', req.convenio.nomeConvenio.valor);
      
      // Atualizar no card de paciente
      setPatientData(prev => ({
        ...prev,
        insurance: req.convenio.nomeConvenio.valor
      }));
      console.log('[PREENCHER] 📝 Convênio atualizado no card do paciente');
    }

    // ✅ FONTE PAGADORA - Entidade que paga (se vier separado)
    if (req.convenio?.nome_fonte_pagadora?.valor) {
      atualizacoesOCR.fontePagadora = req.convenio.nome_fonte_pagadora.valor;
      camposPreenchidos.push('Fonte Pagadora (OCR)');
      console.log('[PREENCHER] ⚠️ Fonte pagadora (campo legado):', req.convenio.nome_fonte_pagadora.valor);
      
      // Atualizar no card de paciente lateral
      setPatientData(prev => ({
        ...prev,
        payingSource: req.convenio.nome_fonte_pagadora.valor
      }));
      console.log('[PREENCHER] 📝 Fonte pagadora atualizada no card do paciente');
    }

    // Exames - BUSCAR IDS AUTOMATICAMENTE
    console.log('[PREENCHER] 🔬 === VERIFICANDO EXAMES ===');
    console.log('[PREENCHER] req existe?', !!req);
    console.log('[PREENCHER] req.requisicao existe?', !!req?.requisicao);
    console.log('[PREENCHER] req.requisicao completo:', JSON.stringify(req?.requisicao, null, 2));
    console.log('[PREENCHER] req.requisicao.itens_exame:', req.requisicao?.itens_exame);
    console.log('[PREENCHER] É array?', Array.isArray(req.requisicao?.itens_exame));
    console.log('[PREENCHER] Length:', req.requisicao?.itens_exame?.length);

    if (req.requisicao?.itens_exame && Array.isArray(req.requisicao.itens_exame) && req.requisicao.itens_exame.length > 0) {
      console.log('[PREENCHER] 🔍 Encontrados', req.requisicao.itens_exame.length, 'exames');
      console.log('[PREENCHER] 🔍 Buscando IDs dos exames no banco de dados...');

      const nomesExames = req.requisicao.itens_exame.map(ex => {
        if (typeof ex === 'object') {
          return ex.descricao_ocr || ex.descricao || String(ex);
        }
        return String(ex);
      });

      console.log('[PREENCHER] Nomes extraídos:', nomesExames);

      try {
        const responseBusca = await apiFetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nomes_exames: nomesExames })
        });

        const resultBusca = await responseBusca.json();

        console.log('[PREENCHER] ✓ Resposta completa da busca:', resultBusca);
        console.log('[PREENCHER] ✓ Total solicitado:', resultBusca.total_solicitado);
        console.log('[PREENCHER] ✓ Total encontrado:', resultBusca.total_encontrado);
        console.log('[PREENCHER] ✓ Resultados detalhados:', resultBusca.resultados);

        if (resultBusca.sucesso && resultBusca.resultados) {
          // Pegar IDs dos exames encontrados
          const idsEncontrados = resultBusca.resultados
            .filter(r => r.encontrado && r.idExame)
            .map(r => r.idExame);

          console.log('[PREENCHER] ✓ IDs filtrados:', idsEncontrados);

          // IMPORTANTE: Pegar TODOS os nomes dos exames do OCR (encontrados E não encontrados)
          // para preencher o campo "EXAMES CONVÊNIO"
          atualizacoesOCR.examesConvenio = nomesExames.join(', ');
          camposPreenchidos.push(`${nomesExames.length} exame(s) do OCR`);
          console.log('[PREENCHER] ✓ TODOS os nomes dos exames para campo EXAMES CONVÊNIO:', nomesExames.join(', '));

          // Atualizar também no card lateral do paciente
          setPatientData(prev => ({
            ...prev,
            exams: nomesExames.join('\n')
          }));
          console.log('[PREENCHER] ✓ Exames atualizados no card lateral do paciente');

          if (idsEncontrados.length > 0) {
            // Usar o primeiro exame como idExame principal
            atualizacoesOCR.idExame = idsEncontrados[0].toString();
            camposPreenchidos.push('ID Exame Principal');
            console.log('[PREENCHER] ✓ ID Exame Principal:', idsEncontrados[0]);
          }

          // Mostrar estatísticas
          const naoEncontrados = resultBusca.resultados
            .filter(r => !r.encontrado)
            .map(r => r.nome_ocr);

          console.log('[PREENCHER] 📊 Estatísticas:');
          console.log('[PREENCHER]   - Total de exames do OCR:', nomesExames.length);
          console.log('[PREENCHER]   - Exames encontrados no DB:', resultBusca.total_encontrado);
          console.log('[PREENCHER]   - Exames NÃO encontrados no DB:', naoEncontrados.length);

          if (naoEncontrados.length > 0) {
            console.warn('[PREENCHER] ⚠️ Exames não encontrados no banco:', naoEncontrados.join(', '));
          }
        }
      } catch (error) {
        console.error('[PREENCHER] ❌ Erro ao buscar IDs dos exames:', error);
      }
    } else {
      console.warn('[PREENCHER] ⚠️ Nenhum exame encontrado nos dados OCR');
      console.warn('[PREENCHER] Motivo: itens_exame não existe, não é array, ou está vazio');
    }

    // 🆕 PACIENTE - VALIDAR NA RECEITA FEDERAL PRIMEIRO, DEPOIS BUSCAR NO BANCO
    console.log('[PREENCHER] 👤 === VERIFICANDO PACIENTE (CPF) ===');
    console.log('[PREENCHER] req.paciente existe?', !!req?.paciente);

    // Tentar pegar CPF de múltiplos campos possíveis
    const cpfOCR = req.paciente?.NumCPF?.valor ||
                   req.paciente?.cpf?.valor ||
                   req.paciente?.CPF?.valor;

    if (cpfOCR) {
      console.log('[PREENCHER] 🔍 Encontrado CPF no OCR:', cpfOCR);

      // PASSO 1: Validar CPF na Receita Federal
      console.log('[PREENCHER] 📞 PASSO 1: Validando CPF na Receita Federal...');

      let nomeReceitaFederal = null;
      let dataNascReceitaFederal = null;

      try {
        // Extrair data de nascimento do OCR
        let dataNascOCR = req.paciente?.DtaNasc?.valor ||
                         req.paciente?.dtaNasc?.valor ||
                         req.paciente?.DtaNascimento?.valor ||
                         '';

        // Formatar data para DD/MM/YYYY
        if (dataNascOCR) {
          try {
            const dataObj = new Date(dataNascOCR);
            if (!isNaN(dataObj.getTime())) {
              const dia = String(dataObj.getDate()).padStart(2, '0');
              const mes = String(dataObj.getMonth() + 1).padStart(2, '0');
              const ano = dataObj.getFullYear();
              dataNascOCR = `${dia}/${mes}/${ano}`;
            }
          } catch (e) {
            console.warn('[PREENCHER] Erro ao formatar data:', e);
          }
        }

        const responseRF = await apiFetch(`${API_BASE_URL}/api/admissao/validar-cpf`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cpf: cpfOCR,
            data_nascimento_ocr: dataNascOCR
          })
        });

        const resultRF = await responseRF.json();

        if (resultRF.sucesso && resultRF.dados_receita_federal) {
          nomeReceitaFederal = resultRF.dados_receita_federal.nome;
          dataNascReceitaFederal = resultRF.dados_receita_federal.data_nascimento;

          console.log('[PREENCHER] ✅ CPF validado na Receita Federal!');
          console.log('[PREENCHER]   - Nome RF:', nomeReceitaFederal);
          console.log('[PREENCHER]   - Data Nasc RF:', dataNascReceitaFederal);
          console.log('[PREENCHER]   - Situação:', resultRF.dados_receita_federal.situacao_cadastral);

          // 🆕 ATUALIZAR O STATUS DA VALIDAÇÃO RECEITA FEDERAL NA UI
          if (resultRF.comparacao) {
            const temDivergencia = resultRF.comparacao.nome?.divergente ||
                                  resultRF.comparacao.data_nascimento?.divergente;

            setReceitaFederalStatus({
              tipo: temDivergencia ? 'aviso' : 'sucesso',
              mensagem: temDivergencia
                ? '⚠️ CPF validado com divergências'
                : '✅ CPF validado pela Receita Federal',
              detalhes: `Nome: ${nomeReceitaFederal} | Situação: ${resultRF.dados_receita_federal.situacao_cadastral}`,
              comparacao: resultRF.comparacao
            });
          }
        } else {
          console.warn('[PREENCHER] ⚠️ Não foi possível validar na Receita Federal');
          console.warn('[PREENCHER]   Motivo:', resultRF.mensagem || 'Erro desconhecido');

          // 🆕 ATUALIZAR STATUS DE ERRO NA UI
          setReceitaFederalStatus({
            tipo: 'aviso',
            mensagem: 'Validação da Receita Federal falhou',
            detalhes: resultRF.mensagem || 'Não foi possível validar o CPF'
          });
        }
      } catch (errorRF) {
        console.error('[PREENCHER] ❌ Erro ao validar na Receita Federal:', errorRF);
      }

      // PASSO 2: Buscar paciente no banco de dados pelo CPF
      console.log('[PREENCHER] 📂 PASSO 2: Buscando paciente no banco pelo CPF...');

      try {
        const responseBusca = await apiFetch(`${API_BASE_URL}/api/paciente/buscar-por-cpf`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cpf: cpfOCR })
        });

        const resultBusca = await responseBusca.json();
        console.log('[PREENCHER] ✓ Resposta da busca do paciente:', resultBusca);

        if (resultBusca.sucesso && resultBusca.paciente) {
          const idPaciente = resultBusca.paciente.idPaciente;
          const nomeBancoDados = resultBusca.paciente.nome;

          console.log('[PREENCHER] ✅ Paciente encontrado no banco!');
          console.log('[PREENCHER]   - ID:', idPaciente);
          console.log('[PREENCHER]   - Nome no Banco:', nomeBancoDados);
          console.log('[PREENCHER]   - CPF:', cpfOCR);

          // PASSO 3: Comparar nome da Receita Federal com nome do banco
          console.log('[PREENCHER] 🔍 PASSO 3: Validando dados...');

          // Normalizar nomes
          const normalizarNome = (nome) => {
            if (!nome) return '';
            return nome
              .toUpperCase()
              .normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '')
              .trim()
              .replace(/\s+/g, ' ');
          };

          // Calcular similaridade
          const calcularSimilaridade = (str1, str2) => {
            if (!str1 || !str2) return 0;
            const palavras1 = str1.split(' ');
            const palavras2 = str2.split(' ');
            let matches = 0;
            palavras1.forEach(p1 => {
              if (palavras2.some(p2 => p2.includes(p1) || p1.includes(p2))) {
                matches++;
              }
            });
            return (matches / Math.max(palavras1.length, palavras2.length)) * 100;
          };

          // Se temos dados da RF, comparar RF vs Banco
          if (nomeReceitaFederal) {
            const nomeRFNormalizado = normalizarNome(nomeReceitaFederal);
            const nomeBancoNormalizado = normalizarNome(nomeBancoDados);
            const similaridade = calcularSimilaridade(nomeRFNormalizado, nomeBancoNormalizado);

            console.log('[PREENCHER] 📊 Comparação RF ↔ Banco:');
            console.log('[PREENCHER]   - Nome RF:', nomeReceitaFederal);
            console.log('[PREENCHER]   - Nome Banco:', nomeBancoDados);
            console.log('[PREENCHER]   - Similaridade:', similaridade.toFixed(1) + '%');

            if (similaridade < 70) {
              // 🚨 ERRO CRÍTICO: Dados da RF não batem com o banco!
              console.error('[PREENCHER] 🚨 ERRO CRÍTICO: Nome na Receita Federal difere do banco!');
              console.error('[PREENCHER]   CPF:', cpfOCR);
              console.error('[PREENCHER]   Nome Receita Federal:', nomeReceitaFederal);
              console.error('[PREENCHER]   Nome no Banco:', nomeBancoDados);
              console.error('[PREENCHER]   🔥 O CADASTRO NO BANCO ESTÁ ERRADO!');

              setMessage({
                type: 'error',
                text: `🚨 ERRO NO CADASTRO! CPF ${cpfOCR} pertence a "${nomeReceitaFederal}" (Receita Federal), mas no banco está cadastrado como "${nomeBancoDados}". CORRIJA O CADASTRO NO BANCO DE DADOS!`
              });

              // NÃO preencher o ID
              console.warn('[PREENCHER] ⚠️ idPaciente NÃO preenchido - CADASTRO INVÁLIDO');
            } else {
              // ✅ Nomes batem!
              console.log('[PREENCHER] ✅ Validação bem-sucedida! Nomes conferem.');
              atualizacoesOCR.idPaciente = idPaciente.toString();
              camposPreenchidos.push('0040000192008nte (CPF)');

              setMessage({
                type: 'success',
                text: `✅ CPF validado! ID: ${idPaciente} - ${nomeReceitaFederal} (Receita Federal)`
              });
            }
          } else {
            // Não temos dados da RF, usar validação simples OCR vs Banco
            const nomeOCR = req.paciente?.NomPaciente?.valor ||
                           req.paciente?.nomePaciente?.valor ||
                           req.paciente?.nome?.valor;

            const nomeOCRNormalizado = normalizarNome(nomeOCR);
            const nomeBancoNormalizado = normalizarNome(nomeBancoDados);
            const similaridade = calcularSimilaridade(nomeOCRNormalizado, nomeBancoNormalizado);

            console.log('[PREENCHER] ⚠️ Receita Federal indisponível, validando OCR vs Banco');
            console.log('[PREENCHER]   - Nome OCR:', nomeOCR);
            console.log('[PREENCHER]   - Nome Banco:', nomeBancoDados);
            console.log('[PREENCHER]   - Similaridade:', similaridade.toFixed(1) + '%');

            if (similaridade < 70 && nomeOCR && nomeBancoDados) {
              console.warn('[PREENCHER] ⚠️ DIVERGÊNCIA: Nome OCR vs Banco');
              setMessage({
                type: 'warning',
                text: `⚠️ Divergência detectada! OCR: "${nomeOCR}" | Banco: "${nomeBancoDados}". Verifique se o cadastro está correto. (Receita Federal indisponível)`
              });

              // Preencher mesmo assim, mas com aviso
              atualizacoesOCR.idPaciente = idPaciente.toString();
              camposPreenchidos.push('ID Paciente (CPF - com divergência)');
            } else {
              atualizacoesOCR.idPaciente = idPaciente.toString();
              camposPreenchidos.push('ID Paciente (CPF)');
              setMessage({
                type: 'success',
                text: `✅ Paciente encontrado! ID: ${idPaciente} - ${nomeBancoDados} (Validação RF indisponível)`
              });
            }
          }
        } else {
          console.warn('[PREENCHER] ⚠️ Paciente não encontrado no banco de dados');
          console.warn('[PREENCHER]   CPF buscado:', cpfOCR);
          console.warn('[PREENCHER]   Resposta:', resultBusca.erro || 'Sem detalhes');

          if (nomeReceitaFederal) {
            setMessage({
              type: 'warning',
              text: `⚠️ CPF ${cpfOCR} validado na Receita Federal (${nomeReceitaFederal}), mas NÃO está cadastrado no sistema. CADASTRE O PACIENTE PRIMEIRO!`
            });
          } else {
            setMessage({
              type: 'warning',
              text: `⚠️ Paciente com CPF ${cpfOCR} não encontrado. Cadastre primeiro.`
            });
          }
        }
      } catch (error) {
        console.error('[PREENCHER] ❌ Erro ao buscar paciente:', error);
        setMessage({
          type: 'error',
          text: `❌ Erro ao buscar paciente: ${error.message}`
        });
      }
    } else {
      console.warn('[PREENCHER] ⚠️ CPF não encontrado no OCR');
    }

    // Médico - BUSCAR ID AUTOMATICAMENTE PELO CRM
    console.log('[PREENCHER] 🩺 === VERIFICANDO MÉDICO ===');
    console.log('[PREENCHER] req.medico existe?', !!req?.medico);
    console.log('[PREENCHER] req.medico completo:', JSON.stringify(req?.medico, null, 2));

    if (req.medico?.numConselho?.valor && req.medico?.ufConselho?.valor) {
      const crm = req.medico.numConselho.valor;
      const uf = req.medico.ufConselho.valor;

      console.log('[PREENCHER] 🔍 Encontrado CRM no OCR:', crm, '/', uf);
      console.log('[PREENCHER] 🔍 Buscando idMedico no banco de dados...');

      try {
        const responseBusca = await apiFetch(`${API_BASE_URL}/api/medicos/${crm}/${uf}`, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' }
        });

        const resultBusca = await responseBusca.json();

        console.log('[PREENCHER] ✓ Resposta da busca do médico:', resultBusca);

        if (resultBusca.sucesso && resultBusca.medico) {
          const idMedico = resultBusca.medico.id;
          const nomeMedico = resultBusca.medico.nome;

          atualizacoesOCR.idMedico = idMedico.toString();
          camposPreenchidos.push('ID Médico (CRM)');

          console.log('[PREENCHER] ✅ Médico encontrado!');
          console.log('[PREENCHER]   - ID:', idMedico);
          console.log('[PREENCHER]   - Nome:', nomeMedico);
          console.log('[PREENCHER]   - CRM:', crm, '/', uf);

          // Atualizar dados do médico no card lateral
          setPatientData(prev => ({
            ...prev,
            doctorName: nomeMedico,
            doctorCRM: `CRM: ${crm}/${uf}`
          }));
        } else {
          console.warn('[PREENCHER] ⚠️ Médico não encontrado no banco de dados');
          console.warn('[PREENCHER]   CRM buscado:', crm, '/', uf);
          console.warn('[PREENCHER]   Resposta:', resultBusca.erro || 'Sem detalhes');

          // Atualizar apenas o CRM no card, sem ID
          setPatientData(prev => ({
            ...prev,
            doctorCRM: `CRM: ${crm}/${uf} (não cadastrado)`
          }));
        }
      } catch (error) {
        console.error('[PREENCHER] ❌ Erro ao buscar médico:', error);
      }
    } else {
      console.warn('[PREENCHER] ⚠️ CRM ou UF não encontrados no OCR');
      console.warn('[PREENCHER]   numConselho:', req.medico?.numConselho?.valor);
      console.warn('[PREENCHER]   ufConselho:', req.medico?.ufConselho?.valor);
    }

    // Atualizar formulário - mesclar com valores existentes
    setFormData(prev => ({
      ...prev,
      ...atualizacoesOCR
    }));

    // Atualizar dados do paciente no card lateral com dados do OCR
    if (req.paciente && Object.keys(req.paciente).length > 0) {
      console.log('[PREENCHER] 👤 Processando dados do paciente do OCR...');
      console.log('[PREENCHER] 🔍 Dados brutos do paciente:', req.paciente);
      console.log('[PREENCHER] 🔍 Total de campos no paciente:', Object.keys(req.paciente).length);
      console.log('[PREENCHER] 🔍 Nomes dos campos:', Object.keys(req.paciente));

      // NÃO tentar adivinhar campos - apenas processar os que existem
      // e adicionar APENAS se tiverem valor
      setPatientData(prev => {
        console.log('[PREENCHER] 📦 Estado anterior do card:', prev);

        const novosDados = { ...prev };

        // 🆕 ADICIONAR ID DO PACIENTE se foi encontrado
        if (atualizacoesOCR.idPaciente) {
          novosDados.idPaciente = atualizacoesOCR.idPaciente;
          console.log('[PREENCHER] ✓ ID Paciente:', atualizacoesOCR.idPaciente);
        }

        // 🚨 PRIORIDADE: Se Receita Federal validou, não sobrescrever nome, CPF e data de nascimento
        const receitaFederalValidou = receitaFederalStatus && receitaFederalStatus.tipo === 'sucesso';
        if (receitaFederalValidou) {
          console.log('[PREENCHER] 🔒 Dados da Receita Federal têm prioridade - bloqueando sobrescrita de nome, CPF e data de nascimento');
        }

        // Processar cada campo do OCR e adicionar se tiver valor (sobrescreve se necessário)
        Object.entries(req.paciente).forEach(([key, obj]) => {
          // Pular o campo 'endereco' aqui, será processado separadamente depois
          if (key === 'endereco') return;

          const valor = obj?.valor;
          if (valor !== null && valor !== undefined && valor !== '') {
            console.log(`[PREENCHER] ✓ Campo OCR ${key}:`, valor);

            // 🆕 MAPEAMENTO EXPANDIDO - Suporta todos os formatos possíveis
            // Nome do paciente
            if (key === 'NomPaciente' || key === 'nome' || key === 'NomePaciente' || key === 'Nome') {
              if (!receitaFederalValidou || !prev.name) {
                novosDados.name = valor;
              } else {
                console.log('[PREENCHER] ⚠️ Nome OCR ignorado - Receita Federal tem prioridade:', prev.name);
              }
            }
            // Data de nascimento
            else if (key === 'DtaNascimento' || key === 'DtaNasc' || key === 'dtaNasc' || key === 'dataNascimento') {
              if (!receitaFederalValidou || !prev.birthDate) {
                novosDados.birthDate = formatarData(valor);
                novosDados.age = `${calcularIdade(valor)} anos`;
              } else {
                console.log('[PREENCHER] ⚠️ Data nascimento OCR ignorada - Receita Federal tem prioridade:', prev.birthDate);
              }
            }
            // CPF
            else if (key === 'NumCPF' || key === 'cpf' || key === 'CPF' || key === 'NumCpf') {
              if (!receitaFederalValidou || !prev.cpf) {
                novosDados.cpf = valor;
              } else {
                console.log('[PREENCHER] ⚠️ CPF OCR ignorado - Receita Federal tem prioridade:', prev.cpf);
              }
            }
            // RG - SEMPRE sobrescrever se vier do OCR e o atual estiver vazio
            else if (key === 'NumRG' || key === 'rg' || key === 'RG' || key === 'RGNumero' || key === 'rgNumero') {
              if (!prev.rg || prev.rg === 'Não informado' || prev.rg === 'null') {
                novosDados.rg = valor;
                console.log('[PREENCHER] ✓ RG preenchido:', valor);
              }
            }
            // Telefone - SEMPRE sobrescrever se vier do OCR e o atual estiver vazio
            else if (key === 'TelCelular' || key === 'telCelular' || key === 'Telefone' || key === 'telefone' || key === 'celular') {
              if (!prev.phone || prev.phone === 'Não informado' || prev.phone === 'null') {
                novosDados.phone = valor;
                console.log('[PREENCHER] ✓ Telefone preenchido:', valor);
              }
            }
            // Email - SEMPRE sobrescrever se vier do OCR e o atual estiver vazio
            else if (key === 'email' || key === 'Email' || key === 'E-mail') {
              if (!prev.email || prev.email === 'Não informado' || prev.email === 'null') {
                novosDados.email = valor;
                console.log('[PREENCHER] ✓ Email preenchido:', valor);
              }
            }
            // Número da carteirinha - SEMPRE sobrescrever se vier do OCR e o atual estiver vazio
            else if (key === 'MatConvenio' || key === 'matriculaConvenio' || key === 'numeroCarteirinha') {
              if (!prev.insuranceCardNumber || prev.insuranceCardNumber === 'Não informado' || prev.insuranceCardNumber === 'null') {
                novosDados.insuranceCardNumber = valor;
                console.log('[PREENCHER] ✓ Nº Carteirinha preenchido:', valor);
              }
            }
            // Sexo
            else if (key === 'sexo' || key === 'Sexo') {
              novosDados.gender = valor;
            }
          }
        });

        // 🆕 PROCESSAR ENDEREÇO (pode ser um objeto com subfields)
        if (req.paciente.endereco) {
          const endereco = req.paciente.endereco;
          console.log('[PREENCHER] 🏠 Processando endereço:', endereco);

          // Se endereco for um objeto com subfields
          if (typeof endereco === 'object' && endereco !== null) {
            const enderecoPartes = [];

            // Extrair valores de cada parte do endereço
            const logradouro = endereco.logradouro?.valor || endereco.Logradouro?.valor;
            const numEndereco = endereco.numEndereco?.valor || endereco.NumEndereco?.valor;
            const complemento = endereco.complemento?.valor || endereco.Complemento?.valor;
            const bairro = endereco.bairro?.valor || endereco.Bairro?.valor;
            const cidade = endereco.cidade?.valor || endereco.Cidade?.valor;
            const uf = endereco.uf?.valor || endereco.UF?.valor;
            const cep = endereco.cep?.valor || endereco.CEP?.valor;

            // Montar endereço completo
            if (logradouro) enderecoPartes.push(logradouro);
            if (numEndereco) enderecoPartes.push(`nº ${numEndereco}`);
            if (complemento) enderecoPartes.push(complemento);
            if (bairro) enderecoPartes.push(bairro);
            if (cidade && uf) enderecoPartes.push(`${cidade}/${uf}`);
            else if (cidade) enderecoPartes.push(cidade);
            else if (uf) enderecoPartes.push(uf);
            if (cep) enderecoPartes.push(`CEP: ${cep}`);

            if (enderecoPartes.length > 0) {
              novosDados.address = enderecoPartes.join(', ');
              console.log('[PREENCHER] ✓ Endereço completo montado:', novosDados.address);
            }
          }
          // Se endereco for uma string direta (formato antigo)
          else if (endereco.valor && typeof endereco.valor === 'string') {
            novosDados.address = endereco.valor;
            console.log('[PREENCHER] ✓ Endereço direto:', novosDados.address);
          }
        }

        // 🆕 BUSCAR MATRÍCULA DO CONVÊNIO (vem em req.convenio, NÃO em req.paciente!)
        if (req.convenio?.matConvenio?.valor) {
          const matriculaOCR = req.convenio.matConvenio.valor;
          // Só preencher se estiver vazio ou "Não informado"
          if (!prev.insuranceCardNumber || prev.insuranceCardNumber === 'Não informado') {
            novosDados.insuranceCardNumber = matriculaOCR;
            console.log('[PREENCHER] ✓ Matrícula do convênio extraída do OCR:', matriculaOCR);
          }
        }

        // Adicionar dados de requisição
        if (req.comentarios_gerais?.requisicao_entrada && !prev.recordNumber) {
          novosDados.recordNumber = req.comentarios_gerais.requisicao_entrada;
        }

        if (req.requisicao?.dtaColeta?.valor && !prev.collectionDate) {
          novosDados.collectionDate = formatarData(req.requisicao.dtaColeta.valor);
        }

        console.log('[PREENCHER] ✅ Dados finais do card:', novosDados);
        console.log('[PREENCHER] 📊 Comparação - Antes vs Depois:');
        console.log('[PREENCHER]   Nome:', prev.name, '→', novosDados.name);
        console.log('[PREENCHER]   CPF:', prev.cpf, '→', novosDados.cpf);
        console.log('[PREENCHER]   RG:', prev.rg, '→', novosDados.rg);
        console.log('[PREENCHER]   Data Nasc:', prev.birthDate, '→', novosDados.birthDate);
        console.log('[PREENCHER]   Telefone:', prev.phone, '→', novosDados.phone);
        console.log('[PREENCHER]   Email:', prev.email, '→', novosDados.email);
        console.log('[PREENCHER]   Nº Carteirinha:', prev.insuranceCardNumber, '→', novosDados.insuranceCardNumber);
        console.log('[PREENCHER]   Endereço:', prev.address, '→', novosDados.address);

        // 🆕 ALERTA se nenhum campo foi alterado
        const camposAlterados = Object.keys(novosDados).filter(key => prev[key] !== novosDados[key]);
        if (camposAlterados.length === 0) {
          console.warn('[PREENCHER] ⚠️ ATENÇÃO: Nenhum campo foi alterado! Verifique se:');
          console.warn('[PREENCHER]   1. Os dados do OCR têm a estrutura correta (key.valor)');
          console.warn('[PREENCHER]   2. A Receita Federal não está bloqueando atualizações');
          console.warn('[PREENCHER]   3. Os campos já tinham valores preenchidos');
        } else {
          console.log(`[PREENCHER] ✅ ${camposAlterados.length} campo(s) alterado(s):`, camposAlterados);
        }

        return novosDados;
      });
    }

    // Atualizar exames no patientData se foram preenchidos
    if (atualizacoesOCR.examesConvenio) {
      setPatientData(prev => ({
        ...prev,
        exams: atualizacoesOCR.examesConvenio
      }));
      console.log('[PREENCHER] ✓ Exames atualizados no card do paciente:', atualizacoesOCR.examesConvenio);
    }

    // 🆕 SINCRONIZAR idPaciente no formData também (necessário para o save)
    if (atualizacoesOCR.idPaciente) {
      setFormData(prev => ({
        ...prev,
        idPaciente: atualizacoesOCR.idPaciente
      }));
      console.log('[PREENCHER] ✓ idPaciente sincronizado no formData:', atualizacoesOCR.idPaciente);
    }

    console.log('[PREENCHER] Formulário atualizado com sucesso!');
    console.log('[PREENCHER] Atualizações OCR aplicadas:', atualizacoesOCR);
    console.log('[PREENCHER] Campos preenchidos:', camposPreenchidos);

    if (camposPreenchidos.length > 0) {
      setMessage({
        type: 'success',
        text: `✓ ${camposPreenchidos.length} campo(s) preenchido(s) pelo OCR: ${camposPreenchidos.join(', ')}`
      });
    } else {
      console.warn('[PREENCHER] ⚠️ ATENÇÃO: OCR processado mas nenhum campo foi preenchido!');
      console.warn('[PREENCHER] ⚠️ Verifique os logs acima para identificar o problema.');
      setMessage({
        type: 'warning',
        text: '⚠️ OCR processado, mas nenhum dado foi preenchido no formulário. Verifique o console (F12) para mais detalhes.'
      });
    }
  };

  // Função para consolidar resultados
  const consolidarResultados = async (dadosOCRParam = null, dadosApiParam = null) => {
    try {
      // Usar dados passados como parâmetro ou do estado
      const dadosParaConsolidar = dadosOCRParam || dadosOCRConsolidados;
      
      // IMPORTANTE: Usar dadosApiParam se fornecido (pois setRequisicaoData é assíncrono)
      const dadosApi = dadosApiParam || requisicaoData;

      // Limpar status de validação anterior antes de processar novo OCR
      setReceitaFederalStatus(null);

      console.log('[CONSOLIDAR] 🔄 Iniciando consolidação...');
      console.log('[CONSOLIDAR] 📸 Dados OCR coletados:', dadosParaConsolidar);
      console.log('[CONSOLIDAR] 📸 Quantidade de imagens processadas:', dadosParaConsolidar.length);
      console.log('[CONSOLIDAR] 🗄️ Dados da API (requisicaoData):', dadosApi);
      console.log('[CONSOLIDAR] 🗄️ Tipo de dadosApi:', typeof dadosApi);
      console.log('[CONSOLIDAR] 🗄️ É array?', Array.isArray(dadosApi));

      // Garantir que dados_api seja um objeto válido
      let dadosParaEnviar = dadosApi;
      if (Array.isArray(dadosApi)) {
        console.warn('[CONSOLIDAR] ATENÇÃO: dadosApi é um array, convertendo...');
        dadosParaEnviar = dadosApi[0] || {};
      }

      // Log detalhado dos dados da API
      if (dadosParaEnviar) {
        console.log('[CONSOLIDAR] 🗄️ Dados do paciente na API:');
        console.log('[CONSOLIDAR]   - Nome:', dadosParaEnviar.paciente?.nome);
        console.log('[CONSOLIDAR]   - CPF:', dadosParaEnviar.paciente?.cpf);
        console.log('[CONSOLIDAR]   - Data Nasc:', dadosParaEnviar.paciente?.dtaNasc);
        console.log('[CONSOLIDAR]   - Telefone:', dadosParaEnviar.paciente?.telCelular);
        console.log('[CONSOLIDAR]   - Email:', dadosParaEnviar.paciente?.email);
        console.log('[CONSOLIDAR]   - Endereço:', dadosParaEnviar.paciente?.endereco);
      }

      const response = await apiFetch(`${API_BASE_URL}/api/consolidar-resultados`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resultados_ocr: dadosParaConsolidar,
          codRequisicao: formData.codRequisicao,
          dados_api: dadosParaEnviar  // Enviar dados da API validados
        })
      });

      const result = await response.json();

      console.log('[CONSOLIDAR] Resposta do backend:', result);
      console.log('[CONSOLIDAR] Resultado consolidado:', result.resultado);

      if (response.ok && result.sucesso) {
        setResultadoConsolidadoFinal(result.resultado);
        console.log('[CONSOLIDAR] Resultado consolidado gerado com sucesso');
        console.log('[CONSOLIDAR] JSON salvo em resultadoConsolidadoFinal');
        console.log('[CONSOLIDAR] 🔍 ESTRUTURA DO RESULTADO:', JSON.stringify(result.resultado, null, 2));

        // 🆕 DETECTAR SINCRONIZAÇÃO 0085 ↔ 0200
        const totalRequisicoes = result.resultado?.requisicoes?.length || 0;
        if (totalRequisicoes > 1) {
          console.log('[CONSOLIDAR] 🔄 Detectadas múltiplas requisições sincronizadas!');
          console.log(`[CONSOLIDAR] Total: ${totalRequisicoes} requisições`);

          const codigosRequisicoes = result.resultado.requisicoes.map(r =>
            r.comentarios_gerais?.requisicao_entrada
          );
          console.log('[CONSOLIDAR] Códigos sincronizados:', codigosRequisicoes);

          // Verificar se há sincronização 0085/0200
          const tem0085 = codigosRequisicoes.some(c => c?.startsWith('0085'));
          const tem0200 = codigosRequisicoes.some(c => c?.startsWith('0200'));

          if (tem0085 && tem0200) {
            console.log('[CONSOLIDAR] ✅ Par 0085/0200 detectado e sincronizado!');
            console.log('[CONSOLIDAR] 🎯 Dados de paciente, médico e convênio são IDÊNTICOS em todas as requisições');

            console.log(`[CONSOLIDAR] Sincronização: ${totalRequisicoes} códigos detectados: ${codigosRequisicoes.join(', ')}`);
          }
        }

        // PREENCHER FORMULÁRIO COM DADOS EXTRAÍDOS - AGUARDAR busca de IDs
        console.log('[CONSOLIDAR] 📝 Chamando preencherFormularioComOCR...');
        await preencherFormularioComOCR(result.resultado);
        console.log('[CONSOLIDAR] ✓ preencherFormularioComOCR concluído');

        // VALIDAR CPF AUTOMATICAMENTE após OCR
        const pacienteOCR = result.resultado?.requisicoes?.[0]?.paciente || {};

        // TENTAR MÚLTIPLOS CAMINHOS PARA PEGAR O CPF (NUNCA usar patientData - pode ser de requisição anterior)
        const cpfExtraido = pacienteOCR.cpf?.valor ||
                           pacienteOCR.NumCPF?.valor ||
                           pacienteOCR.CPF?.valor ||
                           '';

        console.log('[CONSOLIDAR] 🔍 === VALIDAÇÃO RECEITA FEDERAL ===');
        console.log('[CONSOLIDAR] Tentando extrair CPF de:', Object.keys(pacienteOCR));
        console.log('[CONSOLIDAR] CPF encontrado:', cpfExtraido);

        if (cpfExtraido) {
          console.log('[CONSOLIDAR] ✅ CPF extraído do OCR:', cpfExtraido);

          // 🆕 BUSCAR PACIENTE NA API (POR CPF OU NOME) ANTES DE VALIDAR NA RECEITA FEDERAL
          console.log('[CONSOLIDAR] 🔍 Buscando paciente existente na API...');

          // Extrair nome do OCR também
          const pacienteOCR = result.resultado?.requisicoes?.[0]?.paciente || {};
          const nomeExtraido = pacienteOCR.nome?.valor ||
                              pacienteOCR.NomePaciente?.valor ||
                              pacienteOCR.NomPaciente?.valor ||
                              '';

          try {
            let buscaResult = null;
            let metodoBusca = '';

            // Helper: normaliza nome para comparação (sem acento, uppercase, sem espaços extras)
            const normalizarNome = (n) => (n || '').toUpperCase()
              .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
              .replace(/\s+/g, ' ').trim();

            // TENTATIVA 1: Buscar por CPF
            if (cpfExtraido) {
              const cpfLimpo = cpfExtraido.replace(/\D/g, '');
              console.log('[CONSOLIDAR] 🔍 Tentando buscar por CPF:', cpfLimpo);

              const buscaCPFResponse = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cpf: cpfLimpo })
              });

              buscaResult = await buscaCPFResponse.json();
              metodoBusca = 'CPF';

              if (buscaResult.sucesso === 1 && buscaResult.paciente) {
                console.log('[CONSOLIDAR] ✅ Paciente encontrado por CPF:', buscaResult.paciente.nome);

                // Se temos o nome esperado, verificar se o CPF trouxe o paciente certo
                if (nomeExtraido) {
                  const nomeEncontrado = normalizarNome(buscaResult.paciente.nome);
                  const nomeEsperado = normalizarNome(nomeExtraido);
                  if (nomeEncontrado !== nomeEsperado) {
                    console.warn(`[CONSOLIDAR] ⚠️ Nome do CPF ("${nomeEncontrado}") ≠ nome esperado ("${nomeEsperado}"). Tentando por nome...`);
                    // CPF trouxe paciente diferente — tentar pelo nome
                    const buscaNomeResponse2 = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ nome: nomeExtraido })
                    });
                    const resultNome2 = await buscaNomeResponse2.json();
                    if (resultNome2.sucesso === 1 && resultNome2.paciente) {
                      console.log('[CONSOLIDAR] ✅ Nome correto encontrado por NOME:', resultNome2.paciente.nome);
                      buscaResult = resultNome2;
                      metodoBusca = 'NOME';
                    }
                  }
                }
              }
            }

            // TENTATIVA 2: Buscar por NOME (se CPF não encontrou nada)
            if ((!buscaResult || buscaResult.sucesso !== 1) && nomeExtraido) {
              console.log('[CONSOLIDAR] 🔍 CPF não encontrou, tentando buscar por NOME:', nomeExtraido);

              const buscaNomeResponse = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: nomeExtraido })
              });

              buscaResult = await buscaNomeResponse.json();
              metodoBusca = 'NOME';

              if (buscaResult.sucesso === 1 && buscaResult.paciente) {
                console.log('[CONSOLIDAR] ✅ Paciente encontrado por NOME!');
              }
            }

            // PROCESSAR RESULTADO
            if (buscaResult && buscaResult.sucesso === 1 && buscaResult.paciente) {
              const pacienteEncontrado = buscaResult.paciente;
              console.log('[CONSOLIDAR] ✅ PACIENTE ENCONTRADO NA API!');
              console.log('[CONSOLIDAR]   Método:', metodoBusca);
              console.log('[CONSOLIDAR]   ID:', pacienteEncontrado.idPaciente);
              console.log('[CONSOLIDAR]   Nome:', pacienteEncontrado.nome);

              // Preencher idPaciente no formData
              setFormData(prev => ({
                ...prev,
                idPaciente: pacienteEncontrado.idPaciente
              }));

              // Atualizar patientData com dados do cadastro existente (NÃO usar prev para evitar herdar de requisição anterior)
              setPatientData(prev => ({
                ...(prev || {}),
                idPaciente: pacienteEncontrado.idPaciente?.toString() || '',
                name: pacienteEncontrado.nome || '',
                cpf: cpfExtraido || pacienteEncontrado.cpf || '',
                birthDate: pacienteEncontrado.dataNascimento
                  ? new Date(pacienteEncontrado.dataNascimento).toLocaleDateString('pt-BR')
                  : '',
                rg: pacienteEncontrado.rg || '',
                phone: pacienteEncontrado.telefone || '',
                email: pacienteEncontrado.email || ''
              }));

              console.log(`[CONSOLIDAR] Paciente encontrado por ${metodoBusca}: ID=${pacienteEncontrado.idPaciente}, Nome=${pacienteEncontrado.nome}`);
            } else {
              console.log('[CONSOLIDAR] ℹ️ Paciente não encontrado. Novo cadastro será criado ao salvar.');
            }
          } catch (error) {
            console.error('[CONSOLIDAR] ⚠️ Erro ao buscar paciente:', error);
            // Não interromper o fluxo, continuar normalmente
          }

          console.log('[CONSOLIDAR] 📞 Validando CPF na Receita Federal automaticamente...');

          // DEBUG: Ver estrutura completa do paciente no resultado
          console.log('[CONSOLIDAR] 🔍 DEBUG: Estrutura completa do paciente:',
                     JSON.stringify(result.resultado?.requisicoes?.[0]?.paciente, null, 2));
                              
          let dataNascExtraida = pacienteOCR.dtaNasc?.valor || 
                                 pacienteOCR.data_nascimento?.valor ||
                                 pacienteOCR.DtaNascimento?.valor ||
                                 pacienteOCR.DtaNasc?.valor ||
                                 '';

          // FORMATAR DATA PARA DD/MM/YYYY SE VIER EM FORMATO EXTENSO
          if (dataNascExtraida) {
            try {
              // Se vier em formato ISO (YYYY-MM-DD), converter para DD/MM/YYYY
              if (/^\d{4}-\d{2}-\d{2}$/.test(dataNascExtraida)) {
                // Formato ISO: YYYY-MM-DD → DD/MM/YYYY (sem usar Date para evitar problema de timezone)
                const [ano, mes, dia] = dataNascExtraida.split('-');
                dataNascExtraida = `${dia}/${mes}/${ano}`;
                console.log('[CONSOLIDAR] 📅 Data formatada de ISO para DD/MM/YYYY:', dataNascExtraida);
              } else {
                // Tentar com Date() para outros formatos
                const dataObj = new Date(dataNascExtraida + 'T12:00:00'); // Adicionar horário meio-dia para evitar problemas de timezone
                if (!isNaN(dataObj.getTime())) {
                  const dia = String(dataObj.getDate()).padStart(2, '0');
                  const mes = String(dataObj.getMonth() + 1).padStart(2, '0');
                  const ano = dataObj.getFullYear();
                  dataNascExtraida = `${dia}/${mes}/${ano}`;
                  console.log('[CONSOLIDAR] 📅 Data formatada para:', dataNascExtraida);
                }
              }
            } catch (e) {
              console.warn('[CONSOLIDAR] ⚠️ Erro ao formatar data:', e);
            }
          }

          console.log('[CONSOLIDAR] 📝 Dados extraídos do OCR:');
          console.log('[CONSOLIDAR]   Nome:', nomeExtraido);
          console.log('[CONSOLIDAR]   CPF:', cpfExtraido);
          console.log('[CONSOLIDAR]   Data Nascimento:', dataNascExtraida);

          try {
            const responseCPF = await apiFetch(`${API_BASE_URL}/api/admissao/validar-cpf`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                cpf: cpfExtraido,
                nome_ocr: nomeExtraido,
                data_nascimento_ocr: dataNascExtraida
              })
            });

            const resultCPF = await responseCPF.json();
            console.log('[CONSOLIDAR] ✓ Resultado da validação CPF:', resultCPF);

            if (resultCPF.sucesso && resultCPF.dados_receita_federal) {
              const dados = resultCPF.dados_receita_federal;
              console.log('[CONSOLIDAR] ✅ CPF validado com sucesso!');
              console.log('[CONSOLIDAR]   Nome RF:', dados.nome);
              console.log('[CONSOLIDAR]   Situação:', dados.situacao_cadastral);

              // Usar comparação do backend (mais confiável)
              const comparacaoBackend = resultCPF.comparacao || {};

              console.log('[CONSOLIDAR] 📊 Comparação retornada do backend:', comparacaoBackend);

              // 🔍 VERIFICAR DIVERGÊNCIA DE NOME (RF vs Banco) - APENAS AVISAR
              const nomeDiverge = comparacaoBackend.nome?.divergente === true;

              if (nomeDiverge) {
                console.warn('[CONSOLIDAR] ⚠️ Divergência detectada: Nome na RF difere do banco');
                console.warn('[CONSOLIDAR]   Nome RF:', dados.nome);
                console.warn('[CONSOLIDAR]   Nome Banco:', comparacaoBackend.nome?.sistema);
                console.warn('[CONSOLIDAR]   Sistema vai usar dados da RF e permitir salvamento');

                setReceitaFederalStatus({
                  tipo: 'aviso',
                  mensagem: `⚠️ Divergência detectada`,
                  detalhes: `RF: "${dados.nome}" | Banco: "${comparacaoBackend.nome?.sistema}". Usando dados da RF.`,
                  comparacao: comparacaoBackend
                });

                setMessage({
                  type: 'info',
                  text: `ℹ️ Dados atualizados com a Receita Federal: ${dados.nome}`
                });
              } else {
                setReceitaFederalStatus({
                  tipo: 'sucesso',
                  mensagem: 'CPF validado pela Receita Federal',
                  detalhes: `Nome: ${dados.nome} | Situação: ${dados.situacao_cadastral}`,
                  comparacao: comparacaoBackend
                });
              }

              // PRIORIDADE: Atualizar TODOS os dados do card com informações da Receita Federal
              console.log('[CONSOLIDAR] 📝 Aplicando dados da Receita Federal no card...');
              console.log('[CONSOLIDAR]   - Nome RF:', dados.nome);
              console.log('[CONSOLIDAR]   - CPF RF:', dados.cpf);
              console.log('[CONSOLIDAR]   - Data Nasc RF:', dados.data_nascimento);

              setPatientData(prev => {
                const dadosAtualizados = {
                  ...prev,
                  idPaciente: prev.idPaciente, // Preservar ID do paciente
                  name: dados.nome || prev.name,
                  cpf: dados.cpf || prev.cpf
                };

                // Atualizar data de nascimento (formato DD/MM/YYYY)
                if (dados.data_nascimento) {
                  console.log('[CONSOLIDAR] 🔄 Atualizando data de nascimento:', prev.birthDate, '→', dados.data_nascimento);
                  dadosAtualizados.birthDate = dados.data_nascimento;

                  // Recalcular idade com a data correta
                  const partesData = dados.data_nascimento.split('/');
                  if (partesData.length === 3) {
                    const dia = partesData[0];
                    const mes = partesData[1];
                    const ano = partesData[2];
                    const dataNasc = new Date(ano, mes - 1, dia);
                    const hoje = new Date();
                    let idade = hoje.getFullYear() - dataNasc.getFullYear();
                    const mesAtual = hoje.getMonth();
                    const mesNasc = dataNasc.getMonth();
                    if (mesAtual < mesNasc || (mesAtual === mesNasc && hoje.getDate() < dataNasc.getDate())) {
                      idade--;
                    }
                    dadosAtualizados.age = `${idade} anos`;
                  }
                }

                console.log('[CONSOLIDAR] 📝 Dados atualizados no card:', dadosAtualizados);
                return dadosAtualizados;
              });
            } else {
              console.warn('[CONSOLIDAR] ⚠️ CPF não validado:', resultCPF.mensagem);
              setReceitaFederalStatus({
                tipo: 'aviso',
                mensagem: 'CPF não validado',
                detalhes: resultCPF.mensagem || 'Não foi possível validar o CPF na Receita Federal'
              });
            }
          } catch (error) {
            console.error('[CONSOLIDAR] ❌ Erro ao validar CPF:', error);
            setReceitaFederalStatus({
              tipo: 'erro',
              mensagem: 'Erro ao validar CPF',
              detalhes: 'Não foi possível conectar com a API de validação'
            });
          }
        } else {
          console.warn('[CONSOLIDAR] ⚠️ Nenhum CPF extraído do OCR para validar');
          console.warn('[CONSOLIDAR] Estrutura do paciente OCR:', pacienteOCR);
          console.warn('[CONSOLIDAR] Campos disponíveis:', Object.keys(pacienteOCR));

          setReceitaFederalStatus({
            tipo: 'aviso',
            mensagem: 'CPF não encontrado',
            detalhes: 'O OCR não conseguiu extrair o CPF do documento. Valide manualmente.'
          });
        }

        // Forçar scroll para o JSON
        setTimeout(() => {
          const jsonElement = document.querySelector('.json-viewer');
          if (jsonElement) {
            jsonElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }, 100);
      } else {
        console.error('[CONSOLIDAR] Erro na resposta:', result);
        setMessage({
          type: 'error',
          text: `Erro ao consolidar resultados: ${result.erro || 'Erro desconhecido'}`
        });
      }
    } catch (error) {
      console.error('[CONSOLIDAR] Erro:', error);
      setMessage({
        type: 'error',
        text: `Erro ao consolidar resultados: ${error.message}`
      });
    }
  };

  // 🆕 FUNÇÃO PARA VALIDAR CPF MANUALMENTE (BOTÃO NO CARD DO PACIENTE)
  const validarCPFManualmente = async () => {
    console.log('[VALIDAR CPF] 🔍 Iniciando validação manual...');

    // Verificar se tem CPF disponível
    const cpfDisponivel = patientData?.cpf;

    if (!cpfDisponivel) {
      setMessage({
        type: 'error',
        text: '❌ Nenhum CPF disponível para validar. Extraia os dados primeiro usando OCR.'
      });
      return;
    }

    console.log('[VALIDAR CPF] 📋 CPF a ser validado:', cpfDisponivel);

    try {
      setMessage({
        type: 'info',
        text: '🔍 Validando CPF na Receita Federal...'
      });

      const response = await apiFetch(`${API_BASE_URL}/api/admissao/validar-cpf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cpf: cpfDisponivel.replace(/\D/g, ''),
          nome_ocr: patientData?.name,
          data_nascimento_ocr: patientData?.birthDate
        })
      });

      const result = await response.json();
      console.log('[VALIDAR CPF] ✓ Resposta da API:', result);

      if (result.sucesso && result.dados_receita_federal) {
        const dados = result.dados_receita_federal;
        const comparacao = result.comparacao || {};

        console.log('[VALIDAR CPF] ✅ CPF validado com sucesso!');
        console.log('[VALIDAR CPF]   Nome RF:', dados.nome);
        console.log('[VALIDAR CPF]   Data Nasc RF:', dados.data_nascimento);
        console.log('[VALIDAR CPF]   Situação:', dados.situacao_cadastral);

        // Verificar se há divergências
        const temDivergencia = comparacao.nome?.divergente ||
                              comparacao.data_nascimento?.divergente;

        // Atualizar o status da validação na UI
        setReceitaFederalStatus({
          tipo: temDivergencia ? 'aviso' : 'sucesso',
          mensagem: temDivergencia
            ? '⚠️ CPF validado com divergências'
            : '✅ CPF validado pela Receita Federal',
          detalhes: `Nome: ${dados.nome} | Situação: ${dados.situacao_cadastral}`,
          comparacao: comparacao
        });

        // Atualizar dados do paciente com os dados da Receita Federal
        setPatientData(prev => ({
          ...prev,
          name: dados.nome || prev.name,
          cpf: dados.cpf || prev.cpf,
          birthDate: dados.data_nascimento || prev.birthDate
        }));

        setMessage({
          type: temDivergencia ? 'warning' : 'success',
          text: temDivergencia
            ? `⚠️ CPF validado mas há divergências nos dados. Verifique a tabela abaixo.`
            : `✅ CPF validado com sucesso! ${dados.nome} - ${dados.situacao_cadastral}`
        });

        // Scroll para a tabela de validação
        setTimeout(() => {
          const tabelaValidacao = document.querySelector('[style*="background: #f8f9fa"]');
          if (tabelaValidacao) {
            tabelaValidacao.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 500);
      } else {
        console.warn('[VALIDAR CPF] ⚠️ CPF não validado:', result.mensagem);

        setReceitaFederalStatus({
          tipo: 'erro',
          mensagem: 'Erro ao validar CPF',
          detalhes: result.mensagem || 'Não foi possível validar o CPF na Receita Federal'
        });

        setMessage({
          type: 'error',
          text: `❌ ${result.mensagem || 'Não foi possível validar o CPF'}`
        });
      }
    } catch (error) {
      console.error('[VALIDAR CPF] ❌ Erro:', error);

      setReceitaFederalStatus({
        tipo: 'erro',
        mensagem: 'Erro ao conectar com a API',
        detalhes: error.message
      });

      setMessage({
        type: 'error',
        text: `❌ Erro ao validar CPF: ${error.message}`
      });
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Busca automática quando código de requisição tem >= 10 caracteres
    if (name === 'codRequisicao' && value.length >= 10) {
      clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        buscarRequisicao(value);
      }, 800);
    }

    // Sincronizar exames com o card do paciente
    if (name === 'examesConvenio') {
      setPatientData(prev => ({
        ...prev,
        exams: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      // VALIDAÇÃO: Verificar se a requisição foi buscada
      if (!formData.codRequisicao) {
        setMessage({
          type: 'error',
          text: '⚠️ Por favor, digite o código da requisição e clique em "Buscar" antes de salvar.'
        });
        setLoading(false);
        return;
      }

      // 🆕 NÃO BUSCAR AUTOMATICAMENTE - usar apenas dados do OCR
      // O idPaciente já foi buscado pelo CPF durante o OCR
      console.log('[SALVAR] 📋 Usando dados do formulário preenchidos pelo OCR');
      console.log('[SALVAR]   - idPaciente:', formData.idPaciente);
      console.log('[SALVAR]   - Exames:', formData.examesConvenio);

      // 🆕 Usar dados do formData (preenchidos pelo OCR)
      const idPacienteParaSalvar = formData.idPaciente;
      const dtaColetaParaSalvar = formData.dtaColeta;

      // ⚠️ IMPORTANTE: idPaciente pode NÃO existir se for cadastro novo via OCR!
      // O backend vai aceitar sem idPaciente e o apLIS cria automaticamente
      if (!idPacienteParaSalvar) {
        console.log('[SALVAR] ⚠️ idPaciente não encontrado - será um CADASTRO NOVO');
        console.log('[SALVAR] O apLIS irá criar o paciente automaticamente com os dados do OCR');
        setMessage({
          type: 'info',
          text: '📝 Cadastrando novo paciente com dados do OCR...'
        });
      }

      // Data de coleta é obrigatória - usar data atual se não tiver
      const dtaColetaFinal = dtaColetaParaSalvar || new Date().toISOString().split('T')[0];

      if (!dtaColetaParaSalvar) {
        console.log('[SALVAR] ⚠️ Data de coleta não informada, usando data atual:', dtaColetaFinal);
      }

      // Verificar se tem exames
      if (!formData.examesConvenio || formData.examesConvenio.trim() === '') {
        setMessage({
          type: 'error',
          text: '⚠️ Por favor, preencha os exames ou clique em "Iniciar Análise Automática" para extrair automaticamente.'
        });
        setLoading(false);
        return;
      }

      // Helper para converter string para int seguro
      const safeParseInt = (value) => {
        const parsed = parseInt(value);
        return isNaN(parsed) ? undefined : parsed;
      };

      // 🆕 CONVERTER NOMES DE EXAMES PARA IDs
      console.log('[SALVAR] 🔄 Convertendo nomes de exames para IDs...');
      const nomesExames = formData.examesConvenio
        .split(',')
        .map(nome => nome.trim())
        .filter(nome => nome.length > 0);

      console.log('[SALVAR] Nomes dos exames:', nomesExames);

      // Buscar IDs dos exames pelo nome
      const responseBusca = await apiFetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nomes_exames: nomesExames })
      });

      const resultBusca = await responseBusca.json();
      console.log('[SALVAR] Resultado da busca de IDs:', resultBusca);

      if (!resultBusca.sucesso || !resultBusca.resultados) {
        setMessage({
          type: 'error',
          text: '❌ Erro ao buscar IDs dos exames. Tente novamente.'
        });
        setLoading(false);
        return;
      }

      // Extrair IDs encontrados
      const idsExames = resultBusca.resultados
        .filter(r => r.encontrado && r.idExame)
        .map(r => r.idExame);

      console.log('[SALVAR] IDs dos exames encontrados:', idsExames);

      if (idsExames.length === 0) {
        setMessage({
          type: 'error',
          text: '❌ Nenhum exame foi encontrado no banco de dados. Verifique os nomes dos exames.'
        });
        setLoading(false);
        return;
      }

      // 🆕 LOG DO ESTADO ATUAL DO FORMDATA ANTES DE MONTAR
      console.log('[SALVAR] 🔍 Estado atual do formData ANTES de montar objeto:');
      console.log('[SALVAR]   formData.idPaciente:', formData.idPaciente);
      console.log('[SALVAR]   formData completo:', formData);
      console.log('[SALVAR]   patientData:', patientData);

      // 🆕 SINCRONIZAR insuranceCardNumber do patientData com formData.matConvenio antes de salvar
      console.log('[SALVAR] 🔄 Sincronizando número da carteirinha...');
      console.log('[SALVAR]   formData.matConvenio (atual):', formData.matConvenio);
      console.log('[SALVAR]   patientData.insuranceCardNumber:', patientData?.insuranceCardNumber);
      
      // Se formData.matConvenio está vazio mas patientData tem, usar do patientData
      let matConvenioFinal = formData.matConvenio || '';
      if ((!matConvenioFinal || matConvenioFinal.trim() === '') && patientData?.insuranceCardNumber) {
        matConvenioFinal = patientData.insuranceCardNumber;
        console.log('[SALVAR] ✅ Número da carteirinha sincronizado do patientData:', matConvenioFinal);
      }

      // Montar dados para salvar (usando dados preenchidos pelo OCR)
      const dados = {
        ...formData,
        idLaboratorio: safeParseInt(formData.idLaboratorio) || 1,
        idUnidade: safeParseInt(formData.idUnidade) || 1,
        idPaciente: safeParseInt(formData.idPaciente), // Buscado pelo CPF durante OCR OU EDITADO MANUALMENTE
        dtaColeta: dtaColetaFinal, // Garantir que sempre tenha data
        idConvenio: safeParseInt(formData.idConvenio),
        idLocalOrigem: safeParseInt(formData.idLocalOrigem) || 1,
        idFontePagadora: safeParseInt(formData.idFontePagadora),
        idMedico: safeParseInt(formData.idMedico), // Buscado pelo CRM durante OCR
        idExame: idsExames[0], // Primeiro exame como principal
        examesConvenio: idsExames, // Array com todos os IDs
        numGuia: formData.numGuia || '', // 🆕 Incluir número da guia
        matConvenio: matConvenioFinal, // 🆕 Incluir matrícula do convênio (SINCRONIZADO do patientData)
        fontePagadora: formData.fontePagadora || '', // 🆕 Incluir fonte pagadora (nome)
        // 🆕 CREDENCIAIS DO APLIS DO USUÁRIO LOGADO
        aplis_usuario: usuario?.aplis_usuario || null,
        aplis_senha: usuario?.aplis_senha || null
      };

      console.log('[SALVAR] 🔐 Credenciais apLIS do usuário:', {
        usuario: usuario?.aplis_usuario || 'PADRÃO',
        tem_senha: !!usuario?.aplis_senha
      });

      // 🆕 Se idPaciente estiver vazio, incluir dados do paciente do OCR para criação automática
      if (!dados.idPaciente && patientData) {
        console.log('[SALVAR] 🆕 idPaciente não informado - incluindo dados do paciente do OCR para criação automática');
        
        // ⚠️ AVISO: Verificar se CPF foi validado na Receita Federal
        if (patientData.cpf && !receitaFederalStatus?.validado) {
          const confirmar = window.confirm(
            `⚠️ ATENÇÃO: CPF NÃO VALIDADO NA RECEITA FEDERAL\n\n` +
            `CPF: ${patientData.cpf}\n` +
            `Nome: ${patientData.name || 'não informado'}\n\n` +
            `O CPF informado NÃO foi validado na Receita Federal. ` +
            `O paciente será cadastrado com método alternativo (paciente sem documento válido).\n\n` +
            `Deseja continuar mesmo assim?`
          );
          
          if (!confirmar) {
            console.log('[SALVAR] ❌ Usuário cancelou o cadastro - CPF não validado');
            setMessage({
              type: 'info',
              text: '❌ Cadastro cancelado pelo usuário. CPF não foi validado na Receita Federal.'
            });
            setLoading(false);
            return;
          }
          
          console.log('[SALVAR] ⚠️ Usuário confirmou cadastro mesmo sem validação do CPF');
        }
        
        // Incluir dados do paciente extraídos pelo OCR
        if (patientData.cpf) {
          dados.NumCPF = patientData.cpf.replace(/\D/g, ''); // Remove formatação
          console.log('[SALVAR]   ✓ CPF:', dados.NumCPF);
        }
        
        if (patientData.name) {
          dados.NomPaciente = patientData.name;
          console.log('[SALVAR]   ✓ Nome:', dados.NomPaciente);
        }
        
        if (patientData.phone) {
          dados.TelCelular = patientData.phone.replace(/\D/g, ''); // Remove formatação
          console.log('[SALVAR]   ✓ Telefone:', dados.TelCelular);
        }
        
        if (patientData.birthDate) {
          // Converter de DD/MM/YYYY para YYYY-MM-DD
          const partes = patientData.birthDate.split('/');
          if (partes.length === 3) {
            dados.DtaNasc = `${partes[2]}-${partes[1]}-${partes[0]}`;
            console.log('[SALVAR]   ✓ Data Nascimento:', dados.DtaNasc);
          }
        }
        
        if (patientData.rg) {
          dados.RGNumero = patientData.rg;
          console.log('[SALVAR]   ✓ RG:', dados.RGNumero);
        }

        if (patientData.address) {
          dados.DscEndereco = patientData.address;
          console.log('[SALVAR]   ✓ Endereço:', dados.DscEndereco);
        }

        if (patientData.email) {
          dados.Email = patientData.email;
          console.log('[SALVAR]   ✓ Email:', dados.Email);
        }

        console.log('[SALVAR] 📋 Dados do paciente incluídos para criação automática');
      }

      console.log('[SALVAR] 🔍 Valor de idPaciente após processamento:');
      console.log('[SALVAR]   Original (formData):', formData.idPaciente);
      console.log('[SALVAR]   Após safeParseInt:', dados.idPaciente);

      console.log('[SALVAR] ✅ Conversão concluída!');
      console.log('[SALVAR]   idExame (principal):', dados.idExame);
      console.log('[SALVAR]   examesConvenio (todos):', dados.examesConvenio);

      // Remover undefined
      Object.keys(dados).forEach(key => dados[key] === undefined && delete dados[key]);

      if (!dados.codRequisicao) {
        delete dados.codRequisicao;
      }

      // 🆕 MARCAR SE DADOS VIERAM DO OCR (para priorização no backend)
      if (imagensProcessadas.size > 0 || dadosOCRConsolidados.length > 0) {
        dados._fonte_dados = 'ocr';
        console.log('[SALVAR] 📸 Dados vieram do OCR - marcando para priorização no backend');
      }

      // 🆕 LOG DOS DADOS SENDO ENVIADOS
      console.log('[SALVAR] 📤 Enviando dados para o backend:');
      console.log('[SALVAR] Dados:', JSON.stringify(dados, null, 2));
      console.log('[SALVAR] Campos presentes:', Object.keys(dados));
      console.log('[SALVAR] Exames:', dados.examesConvenio);

      const response = await apiFetch(`${API_BASE_URL}/api/admissao/salvar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
      });

      const result = await response.json();

      // 🆕 LOG DETALHADO DO ERRO
      if (!response.ok) {
        console.error('[SALVAR] ❌ Erro na requisição:');
        console.error('[SALVAR]   Status:', response.status);
        console.error('[SALVAR]   Dados enviados:', dados);
        console.error('[SALVAR]   Resposta do servidor:', result);
      }

      if (result.sucesso === 1) {
        // 🆕 VERIFICAR AVISOS DE DUPLICAÇÃO E VALIDAÇÃO
        console.log('[SALVAR] 📋 Resposta completa:', result);

        // Construir mensagem de sucesso
        let mensagemSucesso = `✅ Admissão salva com sucesso! Código: ${result.codRequisicao}`;
        let tipoMensagem = 'success';

        // AVISO DE DUPLICAÇÃO DETECTADA
        if (result.aviso_duplicacao) {
          const dup = result.aviso_duplicacao;
          console.error('[SALVAR] ❌ DUPLICAÇÃO DETECTADA:', dup);

          const listaPacientes = dup.pacientes.map((p, idx) =>
            `${idx + 1}. ID: ${p.id} - Nome: ${p.nome}`
          ).join('\n');

          console.error(`[SALVAR] DUPLICAÇÃO: CPF=${dup.cpf}, ${dup.quantidade} pacientes: ${listaPacientes}`);

          tipoMensagem = 'error';
        }

        // VERIFICAÇÃO OK
        if (result.verificacao_duplicacao && result.verificacao_duplicacao.status === 'ok') {
          console.log('[SALVAR] ✅ Verificação de duplicação OK:', result.verificacao_duplicacao.mensagem);
          mensagemSucesso += '\n' + result.verificacao_duplicacao.mensagem;
        }

        // AVISO DE MÉTODO ALTERNATIVO (CPF NÃO VALIDADO)
        if (result.aviso_metodo_alternativo) {
          const aviso = result.aviso_metodo_alternativo;
          console.warn('[SALVAR] ⚠️ CPF NÃO VALIDADO:', aviso);
          mensagemSucesso += `\n\n⚠️ ${aviso.mensagem}`;
          if (tipoMensagem === 'success') {
            tipoMensagem = 'warning';
          }
        }

        setMessage({
          type: tipoMensagem,
          text: mensagemSucesso
        });

        // Atualizar código da requisição se foi criada uma nova
        if (!formData.codRequisicao && result.codRequisicao) {
          setFormData(prev => ({
            ...prev,
            codRequisicao: result.codRequisicao
          }));
        }
      } else {
        // 🆕 MENSAGEM DE ERRO DETALHADA
        let mensagemErro = result.erro || 'Erro ao salvar admissão';

        // Se o erro mencionar campos faltando, destacar
        if (mensagemErro.includes('faltando')) {
          mensagemErro = `❌ ${mensagemErro}\n\nVerifique se todos os campos obrigatórios foram preenchidos.`;
        }

        setMessage({
          type: 'error',
          text: mensagemErro
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Erro de conexão: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  // ========== MODO AUTOMÁTICO: Funções ==========

  // Extrair lógica OCR em função reutilizável
  const processarOCRCompleto = async (codRequisicao) => {
    console.log('[AUTO-OCR] Iniciando processamento OCR para requisição:', codRequisicao);

    // 1. Buscar imagens da requisição
    const response = await apiFetch(`${API_BASE_URL}/api/requisicao/${codRequisicao}`);
    const data = await response.json();

    if (!response.ok || !data.sucesso) {
      throw new Error(data.erro || 'Erro ao buscar requisição');
    }

    setRequisicaoData(data.requisicao);
    setImagens(data.imagens || []);

    const imagensParaProcessar = data.imagens || [];
    const dadosOCRColetados = [];

    if (imagensParaProcessar.length === 0) {
      console.log('[AUTO-OCR] Nenhuma imagem encontrada para esta requisição');
      return []; // Retorna array vazio em vez de null — requisição é válida, só sem imagens
    }

    console.log(`[AUTO-OCR] ${imagensParaProcessar.length} imagens para processar`);
    setMessage({ type: 'info', text: `Analisando ${imagensParaProcessar.length} imagens com OCR...` });

    setDadosOCRConsolidados([]);
    setImagensProcessadas(new Set());

    let sucessos = 0;
    let erros = 0;

    for (let i = 0; i < imagensParaProcessar.length; i++) {
      if (autoStopRef.current) {
        console.log('[AUTO-OCR] Parada solicitada pelo usuário');
        break;
      }

      const img = imagensParaProcessar[i];
      console.log(`[AUTO-OCR] Processando imagem ${i + 1}/${imagensParaProcessar.length}: ${img.nome}`);
      setMessage({ type: 'info', text: `Processando ${i + 1}/${imagensParaProcessar.length}: ${img.nome}` });

      try {
        let tentativas = 0;
        let maxTentativas = 3;
        let sucesso = false;

        while (tentativas < maxTentativas && !sucesso) {
          tentativas++;

          if (tentativas > 1) {
            const delayRetry = Math.pow(2, tentativas - 1) * 15000;
            console.log(`[AUTO-OCR] Retry ${tentativas}/${maxTentativas} - Aguardando ${delayRetry/1000}s...`);
            setMessage({ type: 'info', text: `Aguardando ${delayRetry/1000}s para retry (tentativa ${tentativas}/${maxTentativas})...` });
            await new Promise(resolve => setTimeout(resolve, delayRetry));
          }

          try {
            const ocrResponse = await apiFetch(`${API_BASE_URL}/api/ocr/processar`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ imagemUrl: img.url, imagemNome: img.nome })
            });

            const ocrResult = await ocrResponse.json();

            if (ocrResponse.status === 500 && ocrResult.erro && ocrResult.erro.includes('429')) {
              console.warn(`[AUTO-OCR] Rate limit (429) na tentativa ${tentativas}`);
              if (tentativas < maxTentativas) continue;
            }

            if (ocrResponse.ok && ocrResult.sucesso) {
              sucesso = true;
              const dadoImagem = {
                imagem: img.nome,
                timestamp: new Date().toISOString(),
                dados: ocrResult.dados
              };
              dadosOCRColetados.push(dadoImagem);
              setImagensProcessadas(prev => new Set([...prev, img.nome]));
              setDadosOCRConsolidados(prev => [...prev, dadoImagem]);
              sucessos++;
              break;
            } else if (tentativas >= maxTentativas) {
              erros++;
              console.warn(`[AUTO-OCR] Erro na imagem ${i + 1} após ${maxTentativas} tentativas`);
            }
          } catch (fetchError) {
            if (tentativas >= maxTentativas) throw fetchError;
          }
        }
      } catch (imgError) {
        erros++;
        console.error(`[AUTO-OCR] Exceção na imagem ${i + 1}:`, imgError);
      }

      // Delay entre imagens
      if (i < imagensParaProcessar.length - 1) {
        console.log('[AUTO-OCR] Aguardando 10 segundos antes da próxima imagem...');
        await new Promise(resolve => setTimeout(resolve, 10000));
      }
    }

    console.log(`[AUTO-OCR] RESUMO: ${sucessos} sucessos, ${erros} erros de ${imagensParaProcessar.length} imagens`);

    // Consolidar
    if (dadosOCRColetados.length > 0) {
      console.log('[AUTO-OCR] Consolidando resultados...');
      setMessage({ type: 'info', text: 'Gerando JSON consolidado...' });
      await new Promise(resolve => setTimeout(resolve, 1500));
      await consolidarResultados(dadosOCRColetados);
      return dadosOCRColetados;
    }

    return null;
  };

  // Versão do handleSubmit sem confirmações (para modo automático)
  const handleSubmitAutomatico = async () => {
    console.log('[AUTO-SAVE] Iniciando salvamento automático...');
    setLoading(true);
    setMessage({ type: 'info', text: 'Salvando admissão automaticamente...' });

    try {
      if (!formData.codRequisicao) {
        throw new Error('Código da requisição não informado');
      }

      if (!formData.examesConvenio || formData.examesConvenio.trim() === '') {
        throw new Error('Nenhum exame encontrado para salvar');
      }

      const safeParseInt = (value) => {
        const parsed = parseInt(value);
        return isNaN(parsed) ? undefined : parsed;
      };

      // Converter nomes de exames para IDs
      const nomesExames = formData.examesConvenio.split(',').map(nome => nome.trim()).filter(nome => nome.length > 0);
      const responseBusca = await apiFetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nomes_exames: nomesExames })
      });

      const resultBusca = await responseBusca.json();
      if (!resultBusca.sucesso || !resultBusca.resultados) {
        throw new Error('Erro ao buscar IDs dos exames');
      }

      const idsExames = resultBusca.resultados.filter(r => r.encontrado && r.idExame).map(r => r.idExame);
      if (idsExames.length === 0) {
        throw new Error('Nenhum exame encontrado no banco de dados');
      }

      let matConvenioFinal = formData.matConvenio || '';
      if ((!matConvenioFinal || matConvenioFinal.trim() === '') && patientData?.insuranceCardNumber) {
        matConvenioFinal = patientData.insuranceCardNumber;
      }

      const dados = {
        ...formData,
        idLaboratorio: safeParseInt(formData.idLaboratorio) || 1,
        idUnidade: safeParseInt(formData.idUnidade) || 1,
        idPaciente: safeParseInt(formData.idPaciente),
        dtaColeta: formData.dtaColeta || new Date().toISOString().split('T')[0],
        idConvenio: safeParseInt(formData.idConvenio),
        idLocalOrigem: safeParseInt(formData.idLocalOrigem) || 1,
        idFontePagadora: safeParseInt(formData.idFontePagadora),
        idMedico: safeParseInt(formData.idMedico),
        idExame: idsExames[0],
        examesConvenio: idsExames,
        numGuia: formData.numGuia || '',
        matConvenio: matConvenioFinal,
        fontePagadora: formData.fontePagadora || '',
        aplis_usuario: usuario?.aplis_usuario || null,
        aplis_senha: usuario?.aplis_senha || null
      };

      // Se idPaciente vazio, incluir dados do paciente para criação automática (SEM confirmação)
      if (!dados.idPaciente && patientData) {
        console.log('[AUTO-SAVE] idPaciente vazio - incluindo dados do paciente para criação automática');
        if (patientData.cpf) dados.NumCPF = patientData.cpf.replace(/\D/g, '');
        if (patientData.name) dados.NomPaciente = patientData.name;
        if (patientData.phone) dados.TelCelular = patientData.phone.replace(/\D/g, '');
        if (patientData.birthDate) {
          const partes = patientData.birthDate.split('/');
          if (partes.length === 3) dados.DtaNasc = `${partes[2]}-${partes[1]}-${partes[0]}`;
        }
        if (patientData.rg) dados.RGNumero = patientData.rg;
        if (patientData.address) dados.DscEndereco = patientData.address;
        if (patientData.email) dados.Email = patientData.email;
      }

      if (imagensProcessadas.size > 0 || dadosOCRConsolidados.length > 0) {
        dados._fonte_dados = 'ocr';
      }

      Object.keys(dados).forEach(key => dados[key] === undefined && delete dados[key]);
      if (!dados.codRequisicao) delete dados.codRequisicao;

      console.log('[AUTO-SAVE] Enviando dados:', Object.keys(dados));

      const response = await apiFetch(`${API_BASE_URL}/api/admissao/salvar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
      });

      const result = await response.json();

      if (result.sucesso === 1) {
        console.log('[AUTO-SAVE] Admissão salva com sucesso! Código:', result.codRequisicao);
        return { sucesso: true, codRequisicao: result.codRequisicao };
      } else {
        throw new Error(result.erro || 'Erro ao salvar admissão');
      }
    } finally {
      setLoading(false);
    }
  };

  // Limpar formulário entre requisições
  const limparFormulario = () => {
    console.log('[AUTO] Limpando formulário para próxima requisição...');
    setFormData({
      codRequisicao: '',
      idLaboratorio: '1',
      idUnidade: '1',
      idPaciente: '',
      dtaColeta: new Date().toISOString().split('T')[0],
      idConvenio: '',
      idLocalOrigem: '1',
      idFontePagadora: '',
      idMedico: '',
      idExame: '',
      examesConvenio: '',
      numGuia: '',
      matConvenio: '',
      fontePagadora: '',
      dadosClinicos: ''
    });
    setPatientData(null);
    setRequisicaoData(null);
    setImagens([]);
    setDadosOCRConsolidados([]);
    setResultadoConsolidadoFinal(null);
    setImagensProcessadas(new Set());
    setReceitaFederalStatus(null);
    setMessage(null);
  };

  // Iniciar modo automático: buscar requisições e processar OCR de TODAS
  // Resetar sessão travada no Supabase
  const resetarSessao = async () => {
    await resetarSessaoHook();
    setFilaIndice(0);
    setFilaRevisaoIndice(-1);
    autoStopRef.current = false;
    limparFormulario();
    setMessage({ type: 'info', text: 'Sessão resetada. Você pode iniciar uma nova.' });
    console.log('[AUTO] Sessão resetada com sucesso.');
  };

  const iniciarModoAutomatico = async () => {
    console.log('[AUTO] Iniciando modo automático...');

    // Verificar se já existe sessão ativa de OUTRO usuário
    if (sessaoAtiva && (filaStatus === 'processando' || filaStatus === 'revisao') && !euSouProcessador) {
      setMessage({ type: 'error', text: `Já existe uma sessão ativa iniciada por ${sessaoAtiva.iniciado_por_nome}` });
      return;
    }

    setFilaLog([]);
    setFilaIndice(0);
    setFilaRevisaoIndice(-1);
    autoStopRef.current = false;

    try {
      setMessage({ type: 'info', text: 'Buscando requisições pendentes...' });

      const response = await apiFetch(`${API_BASE_URL}/api/requisicoes/disponiveis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aplis_usuario: usuario?.aplis_usuario || null,
          aplis_senha: usuario?.aplis_senha || null,
          limite: 15
        })
      });

      const data = await response.json();

      if (!response.ok || !data.sucesso) {
        throw new Error(data.erro || 'Erro ao buscar requisições disponíveis');
      }

      const requisicoes = data.requisicoes || [];
      console.log(`[AUTO] ${requisicoes.length} requisições encontradas`);

      if (requisicoes.length === 0) {
        setMessage({ type: 'info', text: 'Nenhuma requisição pendente encontrada.' });
        return;
      }

      // Criar sessão compartilhada no Supabase
      const sessaoId = crypto.randomUUID();
      const itensParaInserir = requisicoes.map((req, idx) => ({
        sessao_id: sessaoId,
        cod_requisicao: req.CodRequisicao || req.codRequisicao || req.codigo || req.cod,
        paciente_nome: req.NomPaciente || req.paciente || null,
        cpf: req.NumCPF || req.cpf || null,
        status: 'pendente',
        processado_por: usuario?.id || 'anon',
        ordem: idx
      }));

      await iniciarSessao(sessaoId, itensParaInserir, usuario);
      setMessage({ type: 'info', text: `${requisicoes.length} requisições encontradas. Processando OCR de todas...` });

      // Processar OCR de TODAS sequencialmente (só este cliente roda)
      await processarTodasRequisicoes(sessaoId);

    } catch (error) {
      console.error('[AUTO] Erro ao buscar requisições:', error);
      setMessage({ type: 'error', text: `Erro ao buscar requisições: ${error.message}` });
    }
  };

  // Processar OCR de TODAS as requisições (AFK) — escreve resultados no Supabase
  const processarTodasRequisicoes = async (sessaoId) => {
    // Buscar items diretamente do Supabase (não depender do Realtime que pode não ter propagado ainda)
    const { data: filaDoSupabase, error: filaError } = await supabaseClient
      .from('fila_admissao')
      .select('*')
      .eq('sessao_id', sessaoId)
      .order('ordem', { ascending: true });

    if (filaError) {
      console.error('[AUTO] Erro ao buscar fila do Supabase:', filaError);
      setMessage({ type: 'error', text: `Erro ao carregar fila: ${filaError.message}` });
      return;
    }

    const fila = filaDoSupabase || [];
    const total = fila.length;
    console.log(`[AUTO] Fila carregada do Supabase: ${total} items`, fila);

    if (total === 0) {
      console.error('[AUTO] Fila vazia! sessaoId:', sessaoId);
      setMessage({ type: 'error', text: 'Erro: fila vazia no Supabase.' });
      return;
    }

    for (let i = 0; i < total; i++) {
      const item = fila[i];
      if (!item) continue;

      if (autoStopRef.current) {
        console.log('[AUTO] Parada solicitada pelo usuário');
        setMessage({ type: 'info', text: `Processamento pausado. ${i}/${total} analisadas.` });
        break;
      }

      const codRequisicao = item.cod_requisicao || item.codRequisicao;
      console.log(`[AUTO] Processando ${i + 1}/${total}: ${codRequisicao}`);
      setFilaIndice(i);
      setMessage({ type: 'info', text: `[${i + 1}/${total}] Processando OCR: ${codRequisicao}...` });

      // Marcar como processando no Supabase
      if (item.id) await atualizarItem(item.id, { status: 'processando' });

      // Atualizar progresso da sessão
      await atualizarSessao({ itens_processados: i });

      // Limpar form antes
      limparFormulario();
      await new Promise(resolve => setTimeout(resolve, 2000));

      try {
        // Etapa 1: Buscar requisição
        console.log(`[AUTO] [${i+1}/${total}] Buscando requisição ${codRequisicao}...`);
        setMessage({ type: 'info', text: `[${i + 1}/${total}] Buscando dados: ${codRequisicao}...` });
        await buscarRequisicao(codRequisicao);
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Etapa 2: OCR
        console.log(`[AUTO] [${i+1}/${total}] Processando OCR para ${codRequisicao}...`);
        setMessage({ type: 'info', text: `[${i + 1}/${total}] Analisando imagens: ${codRequisicao}...` });
        const ocrResult = await processarOCRCompleto(codRequisicao);

        if (!ocrResult) {
          console.warn(`[AUTO] [${i+1}/${total}] Sem imagens ou OCR falhou para ${codRequisicao} — salvando dados da API`);
        }

        // Aguardar states propagarem
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Capturar snapshot e salvar no Supabase
        await new Promise(resolve => {
          setFormData(currentFormData => {
            setPatientData(currentPatientData => {
              setResultadoConsolidadoFinal(currentResultado => {
                // Salvar snapshot no Supabase
                if (item.id) {
                  atualizarItem(item.id, {
                    status: 'processado',
                    form_data_snapshot: { ...currentFormData },
                    patient_data_snapshot: currentPatientData ? { ...currentPatientData } : null,
                    resultado_consolidado: currentResultado,
                    paciente_nome: currentPatientData?.name || null,
                    cpf: currentPatientData?.cpf || null
                  });
                }
                resolve();
                return currentResultado;
              });
              return currentPatientData;
            });
            return currentFormData;
          });
        });

        console.log(`[AUTO] [${i+1}/${total}] ${codRequisicao} processado com sucesso!`);

      } catch (error) {
        console.error(`[AUTO] [${i+1}/${total}] Erro em ${codRequisicao}:`, error);
        if (item.id) await atualizarItem(item.id, { status: 'erro', erro: error.message });
      }

      // Delay entre requisições
      if (i < total - 1 && !autoStopRef.current) {
        console.log(`[AUTO] Aguardando 5s antes da próxima requisição...`);
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }

    // Todas processadas — entrar em modo revisão
    console.log(`[AUTO] Processamento concluído! Entrando em modo revisão.`);
    await atualizarSessao({ status: 'revisao', itens_processados: total });
    setFilaRevisaoIndice(-1);
    limparFormulario();
    setMessage({ type: 'success', text: `OCR concluído! Revise e aprove cada requisição.` });
  };

  // Carregar uma requisição processada no formulário para revisão (com lock)
  const carregarRequisicaoDaFila = async (indice) => {
    const item = filaRequisicoes[indice];
    if (!item) {
      console.warn('[AUTO] Item não encontrado:', indice);
      return;
    }

    // Verificar se tem snapshot (campos do Supabase usam snake_case)
    const formSnapshot = item.form_data_snapshot || item.formDataSnapshot;
    const patientSnapshot = item.patient_data_snapshot || item.patientDataSnapshot;
    const resultado = item.resultado_consolidado || item.resultadoConsolidado;

    if (!formSnapshot) {
      console.warn('[AUTO] Requisição não tem dados para carregar:', indice);
      return;
    }

    const codRequisicao = item.cod_requisicao || item.codRequisicao;
    console.log(`[AUTO] Carregando requisição ${codRequisicao} para revisão...`);

    // Adquirir lock no Supabase
    if (item.id) {
      const lockOk = await adquirirLockRevisao(item.id);
      if (!lockOk) {
        setMessage({ type: 'error', text: `Item sendo revisado por ${item.revisado_por_nome || 'outro usuário'}` });
        return;
      }
    }

    // Liberar lock anterior se existia
    if (filaRevisaoIndice >= 0 && filaRevisaoIndice !== indice) {
      const itemAnterior = filaRequisicoes[filaRevisaoIndice];
      if (itemAnterior?.id && itemAnterior.status === 'em_revisao') {
        await liberarLockRevisao(itemAnterior.id);
      }
    }

    setFilaRevisaoIndice(indice);
    setFormData(formSnapshot);
    setPatientData(patientSnapshot);
    if (resultado) setResultadoConsolidadoFinal(resultado);

    setMessage({ type: 'info', text: `Revisando: ${codRequisicao} — ${patientSnapshot?.name || item.paciente_nome || 'Paciente'}` });
  };

  // Aprovar requisição: salvar no APLIS + marcar no Supabase
  const aprovarRequisicao = async () => {
    if (filaRevisaoIndice < 0) return;
    const item = filaRequisicoes[filaRevisaoIndice];
    const codRequisicao = formData.codRequisicao || item.cod_requisicao || item.codRequisicao;

    console.log(`[AUTO] Aprovando requisição ${codRequisicao}...`);
    setMessage({ type: 'info', text: `Salvando ${codRequisicao}...` });

    try {
      const saveResult = await handleSubmitAutomatico();

      // Marcar como salvo no Supabase
      if (item.id) await aprovarItemSupabase(item.id, usuario?.id);

      setFilaLog(prev => [...prev, {
        codRequisicao,
        status: 'sucesso',
        mensagem: `Salvo por ${usuario?.nome_completo || usuario?.username || 'usuário'}`,
        timestamp: new Date().toLocaleTimeString()
      }]);

      setMessage({ type: 'success', text: `${codRequisicao} salvo com sucesso!` });
      console.log(`[AUTO] ${codRequisicao} salvo!`);

      limparFormulario();
      setFilaRevisaoIndice(-1);

    } catch (error) {
      console.error(`[AUTO] Erro ao salvar ${codRequisicao}:`, error);
      setMessage({ type: 'error', text: `Erro ao salvar ${codRequisicao}: ${error.message}` });
    }
  };

  // Pular requisição + marcar no Supabase
  const pularRequisicao = async () => {
    if (filaRevisaoIndice < 0) return;
    const item = filaRequisicoes[filaRevisaoIndice];
    const codRequisicao = item.cod_requisicao || item.codRequisicao;

    // Marcar no Supabase
    if (item.id) await pularItemSupabase(item.id);

    setFilaLog(prev => [...prev, {
      codRequisicao,
      status: 'pulado',
      mensagem: `Pulada por ${usuario?.nome_completo || usuario?.username || 'usuário'}`,
      timestamp: new Date().toLocaleTimeString()
    }]);

    limparFormulario();
    setFilaRevisaoIndice(-1);
    setMessage({ type: 'info', text: 'Requisição pulada. Selecione outra para revisar.' });
  };

  // ========== FIM MODO AUTOMÁTICO ==========

  const handleValidate = async () => {
    setLoading(true);
    setMessage(null);

    try {
      const dados = {
        ...formData,
        idLaboratorio: parseInt(formData.idLaboratorio) || undefined,
        idUnidade: parseInt(formData.idUnidade) || undefined,
        idPaciente: parseInt(formData.idPaciente) || undefined,
        idConvenio: parseInt(formData.idConvenio) || undefined,
        idLocalOrigem: parseInt(formData.idLocalOrigem) || undefined,
        idFontePagadora: parseInt(formData.idFontePagadora) || undefined,
        idMedico: parseInt(formData.idMedico) || undefined,
        idExame: parseInt(formData.idExame) || undefined,
        examesConvenio: formData.examesConvenio ?
          formData.examesConvenio.split(',').map(e => parseInt(e.trim())) : undefined
      };

      const response = await apiFetch(`${API_BASE_URL}/api/admissao/validar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
      });

      const result = await response.json();

      if (result.valido) {
        setMessage({
          type: 'success',
          text: result.avisos.length > 0
            ? `Dados válidos! Avisos: ${result.avisos.join(', ')}`
            : 'Dados válidos!'
        });
      } else {
        setMessage({
          type: 'error',
          text: `Erros encontrados: ${result.erros.join(', ')}`
        });
      }
    } catch (error) {
      setMessage({
        type: 'error',
        text: `Erro ao validar: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  // Funções auxiliares
  const calcularIdade = (dtaNasc) => {
    // Validações iniciais
    if (!dtaNasc || dtaNasc === 'null' || dtaNasc === 'undefined') {
      console.warn('[calcularIdade] Data de nascimento inválida:', dtaNasc);
      return 0;
    }

    try {
      let nascimento;

      // Tentar diferentes formatos de data
      if (typeof dtaNasc === 'string') {
        if (dtaNasc.includes('/')) {
          // Formato brasileiro: DD/MM/YYYY
          const [dia, mes, ano] = dtaNasc.split('/');
          nascimento = new Date(parseInt(ano), parseInt(mes) - 1, parseInt(dia));
        } else if (dtaNasc.includes('-')) {
          // Formato ISO: YYYY-MM-DD
          nascimento = new Date(dtaNasc);
        } else {
          nascimento = new Date(dtaNasc);
        }
      } else {
        nascimento = new Date(dtaNasc);
      }

      // Verificar se a data é válida
      if (isNaN(nascimento.getTime())) {
        console.warn('[calcularIdade] Data inválida após conversão:', dtaNasc);
        return 0;
      }

      const hoje = new Date();
      let idade = hoje.getFullYear() - nascimento.getFullYear();
      const mes = hoje.getMonth() - nascimento.getMonth();
      if (mes < 0 || (mes === 0 && hoje.getDate() < nascimento.getDate())) {
        idade--;
      }

      console.log('[calcularIdade] Data:', dtaNasc, '→ Idade:', idade);
      return idade;
    } catch (error) {
      console.error('[calcularIdade] Erro ao calcular idade:', error, 'Data:', dtaNasc);
      return 0;
    }
  };

  const formatarData = (data) => {
    // Validações iniciais
    if (!data || data === 'null' || data === 'undefined') {
      return '';
    }

    try {
      // Se já está no formato brasileiro DD/MM/YYYY, retornar direto
      if (typeof data === 'string' && data.match(/^\d{2}\/\d{2}\/\d{4}$/)) {
        return data;
      }

      // Se é formato ISO YYYY-MM-DD ou objeto Date
      let d;
      if (typeof data === 'string') {
        if (data.includes('/')) {
          const [dia, mes, ano] = data.split('/');
          d = new Date(parseInt(ano), parseInt(mes) - 1, parseInt(dia));
        } else if (data.includes('-')) {
          // Formato ISO: YYYY-MM-DD
          d = new Date(data);
        } else {
          d = new Date(data);
        }
      } else {
        d = new Date(data);
      }

      // Verificar se a data é válida
      if (isNaN(d.getTime())) {
        console.warn('[formatarData] Data inválida:', data);
        return '';
      }

      return d.toLocaleDateString('pt-BR');
    } catch (error) {
      console.error('[formatarData] Erro ao formatar data:', error, 'Data:', data);
      return '';
    }
  };

  const formatarEndereco = (endereco) => {
    if (!endereco) return '';
    const partes = [
      endereco.logradouro,
      endereco.numEndereco,
      endereco.bairro,
      endereco.cidade,
      endereco.uf
    ].filter(Boolean);
    return partes.join(', ');
  };

  // Processar OCR em uma imagem
  const processarOCR = async (imagemUrl, imagemNome, autoProcessamento = false) => {
    // Verificar se já foi processada
    if (imagensProcessadas.has(imagemNome)) {
      console.log(`Imagem ${imagemNome} já foi processada, pulando...`);
      return;
    }

    setLoadingOCR(true);
    if (!autoProcessamento) {
      setMessage(null);
    }

    try {
      const response = await apiFetch(`${API_BASE_URL}/api/ocr/processar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          imagemUrl: imagemUrl,
          imagemNome: imagemNome
        })
      });

      const result = await response.json();

      // DEBUG: Ver o que o backend está retornando
      console.log('[OCR] Resposta completa do backend:', result);
      console.log('[OCR] Dados extraídos:', result.dados);
      if (result.debug_resposta_gemini) {
        console.log('[OCR] Debug Gemini (primeiros 500 chars):', result.debug_resposta_gemini);
      }

      if (response.ok && result.sucesso) {
        // Marcar imagem como processada
        setImagensProcessadas(prev => new Set([...prev, imagemNome]));

        // Adicionar aos dados consolidados
        setDadosOCRConsolidados(prev => [
          ...prev,
          {
            imagem: imagemNome,
            timestamp: new Date().toISOString(),
            dados: result.dados
          }
        ]);

        // Preencher formulário SOMENTE com dados que ainda estão vazios
        if (result.dados) {
          setFormData(prev => {
            const novosDados = {};

            // Verificar cada campo antes de preencher
            Object.keys(result.dados).forEach(key => {
              // Só preencher se o campo estiver vazio
              if (!prev[key] || prev[key] === '') {
                novosDados[key] = result.dados[key];
              }
            });

            return {
              ...prev,
              ...novosDados
            };
          });

          // 🆕 BUSCAR PACIENTE AUTOMATICAMENTE APÓS OCR (POR CPF OU NOME)
          const cpfExtraido = result.dados.cpf || result.dados.NumCPF || result.dados.CPF;
          const nomeExtraido = result.dados.nome || result.dados.NomPaciente || result.dados.NomePaciente;

          if ((cpfExtraido || nomeExtraido) && !formData.idPaciente) {
            console.log('[OCR] 🔍 Dados extraídos:', { cpf: cpfExtraido, nome: nomeExtraido });
            console.log('[OCR] 🔄 Buscando paciente existente na API...');

            try {
              let buscaResult = null;
              let metodoBusca = '';

              // Helper: normaliza nome para comparação
              const normalizarNomeOCR = (n) => (n || '').toUpperCase()
                .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
                .replace(/\s+/g, ' ').trim();

              // TENTATIVA 1: Buscar por CPF
              if (cpfExtraido) {
                const cpfLimpo = cpfExtraido.replace(/\D/g, '');
                console.log('[OCR] 🔍 Tentando buscar por CPF:', cpfLimpo);

                const buscaCPFResponse = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ cpf: cpfLimpo })
                });

                buscaResult = await buscaCPFResponse.json();
                metodoBusca = 'CPF';

                if (buscaResult.sucesso === 1 && buscaResult.paciente) {
                  console.log('[OCR] ✅ Paciente encontrado por CPF:', buscaResult.paciente.nome);

                  // Verificar se o nome bate com o esperado
                  if (nomeExtraido) {
                    const nomeEncontrado = normalizarNomeOCR(buscaResult.paciente.nome);
                    const nomeEsperado = normalizarNomeOCR(nomeExtraido);
                    if (nomeEncontrado !== nomeEsperado) {
                      console.warn(`[OCR] ⚠️ Nome do CPF ("${nomeEncontrado}") ≠ nome esperado ("${nomeEsperado}"). Tentando por nome...`);
                      const buscaNomeResponse2 = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nome: nomeExtraido })
                      });
                      const resultNome2 = await buscaNomeResponse2.json();
                      if (resultNome2.sucesso === 1 && resultNome2.paciente) {
                        console.log('[OCR] ✅ Nome correto encontrado por NOME:', resultNome2.paciente.nome);
                        buscaResult = resultNome2;
                        metodoBusca = 'NOME';
                      }
                    }
                  }
                }
              }

              // TENTATIVA 2: Buscar por NOME (se CPF não encontrou nada)
              if ((!buscaResult || buscaResult.sucesso !== 1) && nomeExtraido) {
                console.log('[OCR] 🔍 CPF não encontrou, tentando buscar por NOME:', nomeExtraido);

                const buscaNomeResponse = await apiFetch(`${API_BASE_URL}/api/buscar-paciente`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ nome: nomeExtraido })
                });

                buscaResult = await buscaNomeResponse.json();
                metodoBusca = 'NOME';

                if (buscaResult.sucesso === 1 && buscaResult.paciente) {
                  console.log('[OCR] ✅ Paciente encontrado por NOME!');
                }
              }

              // PROCESSAR RESULTADO
              if (buscaResult && buscaResult.sucesso === 1 && buscaResult.paciente) {
                const pacienteEncontrado = buscaResult.paciente;
                console.log('[OCR] ✅ Paciente encontrado!', pacienteEncontrado);
                console.log('[OCR]   Método:', metodoBusca);
                console.log('[OCR]   ID:', pacienteEncontrado.idPaciente);
                console.log('[OCR]   Nome:', pacienteEncontrado.nome);

                // Preencher idPaciente no formData
                setFormData(prev => ({
                  ...prev,
                  idPaciente: pacienteEncontrado.idPaciente
                }));

                // Atualizar patientData com dados do cadastro existente
                setPatientData(prev => ({
                  ...prev,
                  idPaciente: pacienteEncontrado.idPaciente?.toString() || prev.idPaciente,
                  name: pacienteEncontrado.nome || prev.name,
                  cpf: cpfExtraido || pacienteEncontrado.cpf,
                  birthDate: pacienteEncontrado.dataNascimento
                    ? new Date(pacienteEncontrado.dataNascimento).toLocaleDateString('pt-BR')
                    : prev.birthDate,
                  rg: pacienteEncontrado.rg || prev.rg,
                  phone: pacienteEncontrado.telefone || prev.phone,
                  email: pacienteEncontrado.email || prev.email
                }));

                if (!autoProcessamento) {
                  setMessage({
                    type: 'success',
                    text: `✅ OCR processado! Paciente ENCONTRADO por ${metodoBusca}: ${pacienteEncontrado.nome} (ID: ${pacienteEncontrado.idPaciente})`
                  });
                }
              } else {
                console.log('[OCR] ℹ️ Paciente não encontrado. Novo cadastro será criado ao salvar.');

                if (!autoProcessamento) {
                  setMessage({
                    type: 'info',
                    text: '📋 OCR processado! Paciente NÃO encontrado - novo cadastro será criado ao salvar.'
                  });
                }
              }
            } catch (error) {
              console.error('[OCR] ⚠️ Erro ao buscar paciente:', error);
              // Não mostrar erro ao usuário, apenas log (busca é opcional)
              if (!autoProcessamento) {
                setMessage({
                  type: 'success',
                  text: 'OCR processado com sucesso! Dados adicionados ao consolidado.'
                });
              }
            }
          } else if (!autoProcessamento) {
            setMessage({
              type: 'success',
              text: 'OCR processado com sucesso! Dados adicionados ao consolidado.'
            });
          }
        }
      } else {
        if (!autoProcessamento) {
          setMessage({
            type: 'error',
            text: result.erro || 'Erro ao processar OCR'
          });
        }
      }
    } catch (error) {
      if (!autoProcessamento) {
        setMessage({
          type: 'error',
          text: `Erro ao processar OCR: ${error.message}`
        });
      }
      console.error('Erro OCR:', error);
    } finally {
      setLoadingOCR(false);
    }
  };

  // Abrir modal de imagem
  const abrirImagem = (imagem) => {
    setImagemSelecionada(imagem);
    setZoomLevel(1); // Resetar zoom ao abrir
  };

  // Fechar modal de imagem
  const fecharModal = () => {
    setImagemSelecionada(null);
    setZoomLevel(1); // Resetar zoom ao fechar
    setModoEdicaoModal(false); // Resetar modo edição
    setDadosEditaveis(null);
    setDadosRequisicaoEditaveis(null);
  };

  // Iniciar edição no modal
  const iniciarEdicaoModal = () => {
    setDadosEditaveis({
      nome: patientData?.name || '',
      dataNascimento: patientData?.birthDate || '',
      cpf: patientData?.cpf || '',
      rg: patientData?.rg || '',
      telefone: patientData?.phone || '',
      email: patientData?.email || '',
      carteirinha: patientData?.insuranceCardNumber || '',
      endereco: patientData?.address || ''
    });
    setDadosRequisicaoEditaveis({
      dataColeta: patientData?.collectionDate || '',
      convenio: patientData?.insurance || '',
      origem: patientData?.origin || '',
      fontePagadora: patientData?.payingSource || '',
      medico: patientData?.doctorName || '',
      crm: patientData?.doctorCRM || '',
      numGuia: requisicaoData?.requisicao?.numGuia || '',
      dadosClinicos: requisicaoData?.requisicao?.dadosClinicos || ''
    });
    setModoEdicaoModal(true);
  };

  // Cancelar edição no modal
  const cancelarEdicaoModal = () => {
    setModoEdicaoModal(false);
    setDadosEditaveis(null);
    setDadosRequisicaoEditaveis(null);
  };

  // Salvar alterações do modal
  const salvarAlteracoesModal = async () => {
    if (!requisicaoData?.paciente?.idPaciente) {
      setMessage({ type: 'error', text: 'ID do paciente não encontrado.' });
      return;
    }

    setSalvandoDados(true);
    try {
      // Salvar dados do paciente
      const responsePaciente = await apiFetch(`${API_BASE_URL}/api/paciente/${requisicaoData.paciente.idPaciente}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          nome: dadosEditaveis.nome,
          dtaNasc: converterDataParaISO(dadosEditaveis.dataNascimento),
          cpf: dadosEditaveis.cpf,
          rg: dadosEditaveis.rg,
          telCelular: dadosEditaveis.telefone,
          email: dadosEditaveis.email,
          matriculaConvenio: dadosEditaveis.carteirinha,
          endereco: dadosEditaveis.endereco
        })
      });

      const dataPaciente = await responsePaciente.json();

      if (!responsePaciente.ok) {
        setMessage({ type: 'error', text: dataPaciente.erro || 'Erro ao atualizar dados do paciente.' });
        setSalvandoDados(false);
        return;
      }

      // Salvar dados da requisição
      const responseRequisicao = await apiFetch(`${API_BASE_URL}/api/requisicao/${formData.codRequisicao}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          dtaColeta: converterDataParaISO(dadosRequisicaoEditaveis.dataColeta),
          convenio: dadosRequisicaoEditaveis.convenio,
          origem: dadosRequisicaoEditaveis.origem,
          fontePagadora: dadosRequisicaoEditaveis.fontePagadora,
          medico: dadosRequisicaoEditaveis.medico,
          crm: dadosRequisicaoEditaveis.crm,
          numGuia: dadosRequisicaoEditaveis.numGuia,
          dadosClinicos: dadosRequisicaoEditaveis.dadosClinicos
        })
      });

      const dataRequisicao = await responseRequisicao.json();

      if (responseRequisicao.ok) {
        // Recalcular idade
        const novaIdade = calcularIdade(converterDataParaISO(dadosEditaveis.dataNascimento));
        
        // Atualizar patientData com novos dados
        setPatientData(prev => ({
          ...prev,
          name: dadosEditaveis.nome,
          birthDate: dadosEditaveis.dataNascimento,
          age: `${novaIdade} anos`,
          cpf: dadosEditaveis.cpf,
          rg: dadosEditaveis.rg,
          phone: dadosEditaveis.telefone,
          email: dadosEditaveis.email,
          insuranceCardNumber: dadosEditaveis.carteirinha,
          address: dadosEditaveis.endereco,
          collectionDate: dadosRequisicaoEditaveis.dataColeta,
          insurance: dadosRequisicaoEditaveis.convenio,
          origin: dadosRequisicaoEditaveis.origem,
          payingSource: dadosRequisicaoEditaveis.fontePagadora,
          doctorName: dadosRequisicaoEditaveis.medico,
          doctorCRM: dadosRequisicaoEditaveis.crm,
          numGuia: dadosRequisicaoEditaveis.numGuia
        }));

        // Atualizar requisicaoData
        setRequisicaoData(prev => ({
          ...prev,
          requisicao: {
            ...prev.requisicao,
            dtaColeta: converterDataParaISO(dadosRequisicaoEditaveis.dataColeta),
            numGuia: dadosRequisicaoEditaveis.numGuia,
            dadosClinicos: dadosRequisicaoEditaveis.dadosClinicos
          }
        }));

        setMessage({ type: 'success', text: '✓ Todos os dados atualizados com sucesso!' });
        setModoEdicaoModal(false);
        setDadosEditaveis(null);
        setDadosRequisicaoEditaveis(null);
      } else {
        setMessage({ type: 'error', text: dataRequisicao.erro || 'Erro ao atualizar dados da requisição.' });
      }
    } catch (error) {
      console.error('Erro ao salvar alterações:', error);
      setMessage({ type: 'error', text: 'Erro ao conectar com o servidor.' });
    } finally {
      setSalvandoDados(false);
    }
  };

  // Controles de zoom
  const zoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.25, 3)); // Max 300%
  };

  const zoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.25, 0.5)); // Min 50%
  };

  const resetZoom = () => {
    setZoomLevel(1);
  };

  // Função para atualizar dados do paciente editados no card
  const handlePatientUpdate = (updatedPatient) => {
    setPatientData(updatedPatient);
    console.log('[PATIENT CARD] Dados do paciente atualizados:', updatedPatient);

    // 🆕 SINCRONIZAR TODOS OS CAMPOS EDITÁVEIS COM O FORMULÁRIO
    setFormData(prev => ({
      ...prev,
      // Sincronizar idPaciente se foi editado
      idPaciente: updatedPatient.idPaciente !== undefined ? updatedPatient.idPaciente : prev.idPaciente,
      // Sincronizar exames se foram editados
      examesConvenio: updatedPatient.exams !== undefined ? updatedPatient.exams : prev.examesConvenio
    }));

    console.log('[PATIENT CARD] ✓ Dados sincronizados com formData');
    console.log('[PATIENT CARD]   - idPaciente:', updatedPatient.idPaciente);
    console.log('[PATIENT CARD]   - exames:', updatedPatient.exams);

    setMessage({
      type: 'success',
      text: '✓ Dados do paciente atualizados com sucesso!'
    });
  };

  // 🆕 Funções para histórico de requisições (Supabase)
  const buscarRequisicoesHistorico = async (filtro = '') => {
    setLoadingHistorico(true);
    try {
      let url = `${API_BASE_URL}/api/historico/listar?limite=50`;

      // Se tiver filtro, buscar por código ou CPF
      if (filtro && filtro.trim()) {
        const filtroLimpo = filtro.trim();
        // Verificar se é CPF (só números) ou código
        if (/^\d{11}$/.test(filtroLimpo)) {
          // É CPF
          url = `${API_BASE_URL}/api/historico/buscar-cpf/${filtroLimpo}`;
        } else {
          // É código de requisição
          url = `${API_BASE_URL}/api/historico/${filtroLimpo}`;
        }
      }

      const response = await apiFetch(url);
      const data = await response.json();

      if (response.ok && data.sucesso === 1) {
        // Normalizar resposta baseado no formato retornado pelo backend
        let requisicoes = [];
        
        if (data.requisicoes) {
          // Resposta de /api/historico/listar: {sucesso: 1, requisicoes: [...]}
          requisicoes = data.requisicoes;
        } else if (data.dados) {
          // Resposta de /api/historico/<cod>: {sucesso: 1, dados: {...}}
          requisicoes = [data.dados];
        } else if (Array.isArray(data)) {
          // Resposta direta como array
          requisicoes = data;
        }
        
        setRequisicoesHistorico(requisicoes);
        setMessage({
          type: 'success',
          text: `✓ ${requisicoes.length} requisição(ões) encontrada(s)`
        });
      } else {
        setMessage({
          type: 'warning',
          text: data.erro || 'Nenhuma requisição encontrada'
        });
        setRequisicoesHistorico([]);
      }
    } catch (error) {
      console.error('Erro ao buscar histórico:', error);
      setMessage({
        type: 'error',
        text: 'Erro ao buscar histórico de requisições'
      });
      setRequisicoesHistorico([]);
    } finally {
      setLoadingHistorico(false);
    }
  };

  const carregarRequisicaoDoHistorico = async (requisicao) => {
    try {
      // Extrair código da requisição e validar
      const codRequisicao = requisicao.cod_requisicao;
      
      console.log('[DEBUG] Carregando requisição do histórico:', requisicao);
      console.log('[DEBUG] Código extraído:', codRequisicao);
      
      if (!codRequisicao) {
        throw new Error('Código da requisição não encontrado');
      }
      
      setMessage({ type: 'info', text: `🔄 Carregando requisição ${codRequisicao}...` });

      // 1. Preencher código e buscar dados completos da API APLIS
      setFormData(prev => ({ ...prev, codRequisicao: codRequisicao }));
      await buscarRequisicao(codRequisicao);

      // 2. Preencher dados consolidados salvos
      if (requisicao.dados_consolidados) {
        setResultadoConsolidadoFinal(requisicao.dados_consolidados);
        await preencherFormularioComOCR(requisicao.dados_consolidados);
      }

      // 3. Restaurar dados do card do paciente se disponível
      if (requisicao.dados_paciente) {
        setPatientData(requisicao.dados_paciente);
      }

      // 4. Preencher exames no campo de texto
      if (requisicao.exames && Array.isArray(requisicao.exames)) {
        const examesString = requisicao.exames.join(', ');
        setFormData(prev => ({
          ...prev,
          examesConvenio: examesString
        }));
        // Atualizar também no card do paciente
        setPatientData(prev => ({
          ...prev,
          exams: examesString
        }));
      }

      setMessage({
        type: 'success',
        text: `✅ Requisição ${codRequisicao} carregada com sucesso!`
      });

      // Fechar o painel de histórico
      setMostrarHistorico(false);

    } catch (error) {
      console.error('Erro ao carregar requisição:', error);
      setMessage({
        type: 'error',
        text: `Erro ao carregar dados da requisição: ${error.message}`
      });
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-neutral-900 overflow-hidden">
      <PatientCard
        patient={patientData}
        onPatientUpdate={handlePatientUpdate}
        onValidarCPF={validarCPFManualmente}
      />

      <div className="flex-1 p-6 bg-slate-50 dark:bg-neutral-900 overflow-y-auto">
        {/* 🆕 Sistema de Abas Principal */}
        <div className="dark:bg-neutral-800 dark:border-neutral-700" style={{
          display: 'flex',
          gap: '0',
          marginBottom: '20px',
          borderBottom: '3px solid #e2e8f0',
          background: 'white'
        }}>
          <button
            type="button"
            onClick={() => setAbaPrincipal('admissao')}
            style={{
              flex: 1,
              padding: '20px',
              background: abaPrincipal === 'admissao' ? '#3b82f6' : 'transparent',
              color: abaPrincipal === 'admissao' ? 'white' : '#64748b',
              border: 'none',
              borderBottom: abaPrincipal === 'admissao' ? '4px solid #2563eb' : '4px solid #e2e8f0',
              cursor: 'pointer',
              fontSize: '18px',
              fontWeight: '600',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px'
            }}
          >
            <span></span>
            <span>Sistema Admissão com OCR</span>
            {abaPrincipal === 'admissao' && <span className="bg-white dark:bg-neutral-700 text-blue-600 dark:text-blue-400 px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider ml-2.5">OCR ATIVO</span>}
          </button>
          <button
            type="button"
            onClick={() => setAbaPrincipal('visualizar')}
            style={{
              flex: 1,
              padding: '20px',
              background: abaPrincipal === 'visualizar' ? '#64748b' : 'transparent',
              color: abaPrincipal === 'visualizar' ? 'white' : '#64748b',
              border: 'none',
              borderBottom: abaPrincipal === 'visualizar' ? '4px solid #475569' : '4px solid #e2e8f0',
              cursor: 'pointer',
              fontSize: '18px',
              fontWeight: '600',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px'
            }}
          >
            <span></span>
            <span>Visualizar Imagens e Dados</span>
          </button>
        </div>

        {/* Conteúdo da aba de Admissão */}
        {abaPrincipal === 'admissao' && (
          <>
        {/* Painel do Modo Automático — Compartilhado */}
        <div className={`${filaStatus === 'processando' ? 'bg-blue-50 dark:bg-blue-950/40 border-2 border-blue-500' : filaStatus === 'revisao' ? 'bg-amber-50 dark:bg-amber-950/30 border-2 border-amber-500' : 'bg-slate-50 dark:bg-neutral-800 border border-slate-200 dark:border-neutral-700'}`} style={{ marginBottom: '20px', padding: '16px', borderRadius: '12px' }}>

          {/* Info da sessão ativa */}
          {sessaoAtiva && (
            <div className="text-xs mb-2" style={{ opacity: 0.7 }}>
              <span className="dark:text-neutral-400 text-slate-500">
                Sessao iniciada por <strong>{sessaoAtiva.iniciado_por_nome || 'Desconhecido'}</strong>
                {euSouProcessador && ' (voce)'}
              </span>
            </div>
          )}

          {/* Barra de controle */}
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
            {(filaStatus === 'idle' || filaStatus === 'concluido') && (
              <button
                type="button"
                onClick={iniciarModoAutomatico}
                disabled={loading || loadingRequisicao}
                style={{ padding: '12px 24px', background: '#3b82f6', color: 'white', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: '600', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.6 : 1 }}
              >
                Iniciar Modo Automatico
              </button>
            )}

            {(filaStatus === 'processando' || filaStatus === 'buscando_fila') && euSouProcessador && (
              <button
                type="button"
                onClick={() => { autoStopRef.current = true; }}
                style={{ padding: '12px 24px', background: '#ef4444', color: 'white', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: '600', cursor: 'pointer' }}
              >
                Parar
              </button>
            )}

            {(filaStatus === 'processando' || filaStatus === 'revisao' || filaStatus === 'buscando_fila') && (
              <button
                type="button"
                onClick={resetarSessao}
                title="Reseta a sessão travada e permite iniciar uma nova"
                style={{ padding: '12px 24px', background: '#6b7280', color: 'white', border: 'none', borderRadius: '8px', fontSize: '15px', fontWeight: '600', cursor: 'pointer' }}
              >
                Reiniciar Sessão
              </button>
            )}

            {filaStatus === 'buscando_fila' && (
              <span className="text-blue-500 dark:text-blue-400" style={{ fontWeight: '500', fontSize: '14px' }}>Buscando requisicoes pendentes...</span>
            )}

            {filaStatus === 'processando' && (
              <span className="text-blue-500 dark:text-blue-400" style={{ fontWeight: '600', fontSize: '15px' }}>
                Processando OCR {(sessaoAtiva?.itens_processados || filaIndice) + 1}/{filaRequisicoes.length}
              </span>
            )}

            {filaStatus === 'revisao' && (
              <span className="text-amber-500 dark:text-amber-400" style={{ fontWeight: '600', fontSize: '15px' }}>
                Revisao — {filaRequisicoes.filter(r => r.status === 'salvo').length} salvos, {filaRequisicoes.filter(r => r.status === 'processado' || r.status === 'em_revisao').length} aguardando
              </span>
            )}

            {filaStatus === 'concluido' && (
              <span className="text-green-600 dark:text-green-400" style={{ fontWeight: '600', fontSize: '15px' }}>
                Concluido — {filaRequisicoes.filter(r => r.status === 'salvo').length} salvos de {filaRequisicoes.length}
              </span>
            )}
          </div>

          {/* Lista de requisições processadas para revisão */}
          {(filaStatus === 'revisao' || filaStatus === 'processando' || filaStatus === 'concluido') && filaRequisicoes.length > 0 && (
            <div className="border border-slate-200 dark:border-neutral-600" style={{ marginTop: '12px', maxHeight: '350px', overflowY: 'auto', borderRadius: '8px' }}>
              {filaRequisicoes.map((item, idx) => {
                const isSelected = idx === filaRevisaoIndice;
                const isDark = document.documentElement.classList.contains('dark');
                const codReq = item.cod_requisicao || item.codRequisicao;
                const nome = item.patient_data_snapshot?.name || item.patientDataSnapshot?.name || item.paciente_nome || item.paciente || '—';
                const cpfItem = item.patient_data_snapshot?.cpf || item.patientDataSnapshot?.cpf || item.cpf || '';
                const isLockedByOther = item.status === 'em_revisao' && item.revisado_por !== usuario?.id;
                const canClick = (item.status === 'processado' || (item.status === 'em_revisao' && item.revisado_por === usuario?.id)) && (filaStatus === 'revisao' || filaStatus === 'processando');
                const statusColors = {
                  pendente: { bg: isDark ? '#1c1c1c' : '#f8fafc', text: '#94a3b8', label: 'Pendente' },
                  processando: { bg: isDark ? '#172554' : '#eff6ff', text: '#60a5fa', label: 'Processando...' },
                  processado: { bg: isDark ? '#1a1a1a' : '#ffffff', text: '#fbbf24', label: 'Aguardando revisao' },
                  em_revisao: { bg: isDark ? '#1e1b4b' : '#eef2ff', text: '#818cf8', label: isLockedByOther ? `Revisando: ${item.revisado_por_nome || '...'}` : 'Em revisao (voce)' },
                  erro: { bg: isDark ? '#2a1215' : '#fef2f2', text: '#f87171', label: 'Erro' },
                  salvo: { bg: isDark ? '#0a2618' : '#f0fdf4', text: '#4ade80', label: 'Salvo' },
                  pulado: { bg: isDark ? '#1c1c1c' : '#f8fafc', text: '#94a3b8', label: 'Pulado' }
                };
                const st = statusColors[item.status] || statusColors.pendente;

                return (
                  <div
                    key={item.id || idx}
                    onClick={() => { if (canClick) carregarRequisicaoDaFila(idx); }}
                    style={{
                      padding: '10px 14px',
                      borderBottom: isDark ? '1px solid #333' : '1px solid #f1f5f9',
                      background: isSelected ? (isDark ? '#422006' : '#fef3c7') : st.bg,
                      cursor: canClick ? 'pointer' : 'default',
                      opacity: isLockedByOther ? 0.6 : 1,
                      display: 'flex',
                      gap: '12px',
                      alignItems: 'center',
                      transition: 'background 0.15s',
                      borderLeft: isSelected ? '4px solid #f59e0b' : '4px solid transparent'
                    }}
                  >
                    <span style={{ fontWeight: '600', fontSize: '14px', minWidth: '120px', color: isDark ? '#e5e5e5' : undefined }}>{codReq}</span>
                    <span style={{ flex: 1, fontSize: '13px', color: isDark ? '#a3a3a3' : '#475569' }}>{nome}</span>
                    <span style={{ fontSize: '12px', color: isDark ? '#737373' : '#64748b' }}>{cpfItem}</span>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      color: st.text,
                      background: isDark ? '#262626' : st.bg,
                      padding: '3px 10px',
                      borderRadius: '12px',
                      border: `1px solid ${st.text}30`,
                      whiteSpace: 'nowrap'
                    }}>
                      {st.label}
                    </span>
                    {item.status === 'erro' && (
                      <span style={{ fontSize: '11px', color: '#f87171' }}>{item.erro}</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Botões de ação quando uma requisição está selecionada para revisão */}
          {(filaStatus === 'revisao' || filaStatus === 'processando') && filaRevisaoIndice >= 0 && (
            <div className="bg-amber-100 dark:bg-amber-900/30 border border-amber-400 dark:border-amber-600" style={{ marginTop: '12px', display: 'flex', gap: '12px', alignItems: 'center', padding: '12px', borderRadius: '8px' }}>
              <span className="text-amber-800 dark:text-amber-300" style={{ fontSize: '14px', fontWeight: '500', flex: 1 }}>
                Revisando: {filaRequisicoes[filaRevisaoIndice]?.cod_requisicao || filaRequisicoes[filaRevisaoIndice]?.codRequisicao} — Edite os campos se necessario, depois aprove ou pule.
              </span>
              <button
                type="button"
                onClick={aprovarRequisicao}
                disabled={loading}
                style={{ padding: '10px 20px', background: '#16a34a', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}
              >
                Aprovar e Salvar
              </button>
              <button
                type="button"
                onClick={pularRequisicao}
                style={{ padding: '10px 20px', background: '#94a3b8', color: 'white', border: 'none', borderRadius: '8px', fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}
              >
                Pular
              </button>
            </div>
          )}

          {/* Instrução quando em modo revisão sem seleção */}
          {filaStatus === 'revisao' && filaRevisaoIndice < 0 && filaRequisicoes.some(r => r.status === 'processado') && (
            <div className="bg-blue-50 dark:bg-blue-950/30 text-blue-800 dark:text-blue-300" style={{ marginTop: '12px', padding: '12px', borderRadius: '8px', fontSize: '14px', fontWeight: '500' }}>
              Clique em uma requisicao da lista acima para revisar e aprovar.
            </div>
          )}

          {/* Verificar se todas foram revisadas */}
          {filaStatus === 'revisao' && !filaRequisicoes.some(r => r.status === 'processado' || r.status === 'em_revisao') && (
            <div className="bg-green-50 dark:bg-green-950/30 text-green-800 dark:text-green-300" style={{ marginTop: '12px', padding: '12px', borderRadius: '8px', fontSize: '14px', fontWeight: '500' }}>
              Todas as requisicoes foram revisadas! {filaRequisicoes.filter(r => r.status === 'salvo').length} salvas, {filaRequisicoes.filter(r => r.status === 'pulado').length} puladas, {filaRequisicoes.filter(r => r.status === 'erro').length} com erro.
            </div>
          )}
        </div>

        {/* Botão para abrir histórico */}
        <div style={{ marginBottom: '20px' }}>
          <button
            type="button"
            onClick={() => {
              setMostrarHistorico(!mostrarHistorico);
              if (!mostrarHistorico) {
                buscarRequisicoesHistorico();
              }
            }}
            style={{
              width: '100%',
              padding: '15px 20px',
              background: '#64748b',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '10px',
              boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
              transition: 'all 0.2s ease'
            }}
          >
            <span style={{ fontSize: '20px' }}></span>
            {mostrarHistorico ? 'Fechar Histórico' : 'Requisições Incompletas'}
          </button>
        </div>

        {/* 🆕 Painel de histórico */}
        {mostrarHistorico && (
          <div className="bg-white dark:bg-neutral-800 border-2 border-emerald-500 dark:border-emerald-600 dark:shadow-lg dark:shadow-emerald-900/20" style={{
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '20px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
          }}>
            <h3 className="text-emerald-600 dark:text-emerald-400" style={{
              margin: '0 0 20px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <span>📋</span> Histórico de Requisições
            </h3>

            {/* Campo de busca */}
            <div style={{ marginBottom: '15px' }}>
              <div style={{ display: 'flex', gap: '10px' }}>
                <input
                  type="text"
                  value={buscaHistorico}
                  onChange={(e) => setBuscaHistorico(e.target.value)}
                  placeholder="Buscar por código ou CPF..."
                  className="bg-white dark:bg-neutral-700 border-gray-300 dark:border-neutral-600 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-400"
                  style={{
                    flex: 1,
                    padding: '10px 15px',
                    border: '2px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      buscarRequisicoesHistorico(buscaHistorico);
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={() => buscarRequisicoesHistorico(buscaHistorico)}
                  disabled={loadingHistorico}
                  className="dark:shadow-lg dark:shadow-sky-900/20"
                  style={{
                    padding: '10px 20px',
                    background: '#0ea5e9',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: loadingHistorico ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                    opacity: loadingHistorico ? 0.5 : 1
                  }}
                >
                  {loadingHistorico ? '🔄' : '🔍'} Buscar
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setBuscaHistorico('');
                    buscarRequisicoesHistorico('');
                  }}
                  disabled={loadingHistorico}
                  className="bg-gray-600 dark:bg-neutral-700 dark:shadow-lg dark:shadow-neutral-900/20"
                  style={{
                    padding: '10px 20px',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: loadingHistorico ? 'not-allowed' : 'pointer',
                    fontWeight: '600',
                    opacity: loadingHistorico ? 0.5 : 1
                  }}
                >
                  Limpar
                </button>
              </div>
              <small className="text-gray-500 dark:text-neutral-400" style={{ display: 'block', marginTop: '8px' }}>
                💡 Digite o código da requisição ou CPF do paciente (11 dígitos)
              </small>
            </div>

            {/* Lista de requisições */}
            {loadingHistorico ? (
              <div className="text-gray-500 dark:text-neutral-400" style={{ textAlign: 'center', padding: '30px' }}>
                <div style={{ fontSize: '32px', marginBottom: '10px' }}>🔄</div>
                <div>Buscando requisições...</div>
              </div>
            ) : requisicoesHistorico.length === 0 ? (
              <div className="text-gray-500 dark:text-neutral-400" style={{ textAlign: 'center', padding: '30px' }}>
                <div style={{ fontSize: '32px', marginBottom: '10px' }}>📋</div>
                <div>Nenhuma requisição encontrada</div>
                <small>Processe algumas requisições para vê-las aqui</small>
              </div>
            ) : (
              <div style={{
                maxHeight: '400px',
                overflowY: 'auto',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}>
                {requisicoesHistorico.map((req, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-50 dark:bg-neutral-700 border border-gray-200 dark:border-neutral-600"
                    style={{
                      borderRadius: '8px',
                      padding: '15px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.2s ease',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = document.documentElement.classList.contains('dark') ? '#3f3f46' : '#f3f4f6';
                      e.currentTarget.style.borderColor = '#10b981';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = document.documentElement.classList.contains('dark') ? '#404040' : '#f9fafb';
                      e.currentTarget.style.borderColor = document.documentElement.classList.contains('dark') ? '#525252' : '#e5e7eb';
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div className="text-gray-900 dark:text-neutral-100" style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                        📄 {req.cod_requisicao}
                      </div>
                      <div className="text-gray-600 dark:text-neutral-300" style={{ fontSize: '13px' }}>
                        👤 {req.nome_paciente || 'Nome não disponível'}
                      </div>
                      {req.cpf_paciente && (
                        <div className="text-gray-600 dark:text-neutral-300" style={{ fontSize: '12px' }}>
                          📋 CPF: {req.cpf_paciente}
                        </div>
                      )}
                      {req.exames && req.exames.length > 0 && (
                        <div className="text-emerald-600 dark:text-emerald-400" style={{ fontSize: '12px', marginTop: '5px' }}>
                          🧪 {req.exames.length} exame(s): {req.exames.slice(0, 2).join(', ')}
                          {req.exames.length > 2 && '...'}
                        </div>
                      )}
                      <div className="text-gray-400 dark:text-neutral-500" style={{ fontSize: '11px', marginTop: '5px' }}>
                        🕒 {new Date(req.created_at).toLocaleString('pt-BR')}
                      </div>

                      {/* Aviso de Campos Faltantes */}
                      {(() => {
                        // Pegar dados do paciente do campo dados_paciente
                        const dadosPaciente = req.dados_paciente || {};

                        // Apenas campos REALMENTE obrigatórios para cadastro pela API
                        const camposObrigatorios = [
                          { campo: 'nome', label: 'Nome', valor: dadosPaciente.nome || dadosPaciente.name || req.nome_paciente },
                          { campo: 'dtaNasc', label: 'Data Nasc.', valor: dadosPaciente.dtaNasc || dadosPaciente.birthDate || req.data_nascimento },
                          { campo: 'cpf', label: 'CPF', valor: dadosPaciente.cpf || req.cpf_paciente },
                          { campo: 'sexo', label: 'Sexo', valor: dadosPaciente.sexo || dadosPaciente.gender }
                        ];

                        const camposFaltantes = camposObrigatorios.filter(item =>
                          !item.valor || (typeof item.valor === 'string' && item.valor.trim() === '')
                        );

                        if (camposFaltantes.length > 0) {
                          return (
                            <div style={{
                              marginTop: '10px',
                              padding: '10px 12px',
                              background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
                              border: '2px solid #ef4444',
                              borderRadius: '6px',
                              fontSize: '12px'
                            }}>
                              <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                marginBottom: '6px',
                                color: '#991b1b',
                                fontWeight: '700'
                              }}>
                                <span>⚠️</span>
                                <span>Campos obrigatórios faltando:</span>
                              </div>
                              <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '5px'
                              }}>
                                {camposFaltantes.map((item, i) => (
                                  <span
                                    key={i}
                                    style={{
                                      background: '#dc2626',
                                      color: 'white',
                                      padding: '3px 8px',
                                      borderRadius: '4px',
                                      fontSize: '11px',
                                      fontWeight: '600',
                                      whiteSpace: 'nowrap'
                                    }}
                                  >
                                    {item.label}
                                  </span>
                                ))}
                              </div>
                            </div>
                          );
                        }
                        return null;
                      })()}
                    </div>
                    <button
                      type="button"
                      onClick={() => carregarRequisicaoDoHistorico(req)}
                      className="dark:shadow-lg dark:shadow-emerald-900/20"
                      style={{
                        padding: '10px 20px',
                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontWeight: '600',
                        fontSize: '14px',
                        whiteSpace: 'nowrap',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                      }}
                    >
                      ⚡ Carregar
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {sincronizacaoInfo && sincronizacaoInfo.sincronizado && (
          <div style={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            padding: '15px 20px',
            borderRadius: '8px',
            marginBottom: '20px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '15px'
          }}>
            <div style={{
              fontSize: '24px',
              background: 'rgba(255,255,255,0.2)',
              width: '45px',
              height: '45px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              🔄
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 'bold', fontSize: '16px', marginBottom: '5px' }}>
                Dados Sincronizados Automaticamente
              </div>
              <div style={{ fontSize: '14px', opacity: 0.95 }}>
                Os dados do paciente foram sincronizados com a requisição correspondente{' '}
                <strong style={{
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontFamily: 'monospace'
                }}>
                  {sincronizacaoInfo.codigoCorrespondente}
                </strong>
              </div>
              <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.9 }}>
                <strong>Campos sincronizados:</strong> {sincronizacaoInfo.camposSincronizados?.join(', ')}
              </div>
            </div>
          </div>
        )}

        {/* 🆕 BANNER DE AVISO DA RECEITA FEDERAL */}
        {receitaFederalStatus && receitaFederalStatus.tipo === 'erro' && (
          <div style={{
            background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)',
            color: 'white',
            padding: '15px 20px',
            borderRadius: '8px',
            marginBottom: '20px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            display: 'flex',
            alignItems: 'center',
            gap: '15px',
            border: '2px solid rgba(255,255,255,0.3)'
          }}>
            <div style={{
              fontSize: '28px',
              background: 'rgba(255,255,255,0.2)',
              width: '50px',
              height: '50px',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              ⚠️
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 'bold', fontSize: '16px', marginBottom: '5px' }}>
                {receitaFederalStatus.mensagem}
              </div>
              <div style={{ fontSize: '14px', opacity: 0.95 }}>
                {receitaFederalStatus.detalhes}
              </div>
              <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.9, fontStyle: 'italic' }}>
                ⓘ Verifique manualmente se o nome, CPF e data de nascimento estão corretos.
              </div>
            </div>
          </div>
        )}

        {receitaFederalStatus && (receitaFederalStatus.tipo === 'sucesso' || receitaFederalStatus.tipo === 'aviso') && (
          <div className="bg-slate-100 dark:bg-neutral-800 text-gray-900 dark:text-neutral-100" style={{
            border: '2px solid #dee2e6',
            padding: '16px 20px',
            borderRadius: '8px',
            marginBottom: '20px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              marginBottom: receitaFederalStatus.comparacao ? '15px' : '0'
            }}>
              <span style={{
                fontSize: '22px',
                flexShrink: 0
              }}>
                {receitaFederalStatus.tipo === 'aviso' ? '⚠️' : '✅'}
              </span>
              <div style={{ flex: 1 }}>
                <div className="text-gray-900 dark:text-neutral-100" style={{ fontWeight: 'bold', fontSize: '15px' }}>
                  {receitaFederalStatus.mensagem}
                </div>
              </div>
            </div>

            {/* Tabela comparativa */}
            {receitaFederalStatus.comparacao && (
              <div className="bg-white dark:bg-neutral-800" style={{
                border: '1px solid #dee2e6',
                borderRadius: '6px',
                padding: '12px',
                fontSize: '13px'
              }}>
                <div className="text-gray-900 dark:text-neutral-100" style={{ fontWeight: 'bold', marginBottom: '10px', fontSize: '14px' }}>
                  📊 Validação dos Dados:
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr className="bg-slate-100 dark:bg-neutral-700" style={{ borderBottom: '2px solid #dee2e6' }}>
                      <th className="text-gray-700 dark:text-neutral-200" style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold' }}>Campo</th>
                      <th className="text-gray-700 dark:text-neutral-200" style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold' }}>Sistema/OCR/API</th>
                      <th className="text-gray-700 dark:text-neutral-200" style={{ padding: '10px', textAlign: 'left', fontWeight: 'bold' }}>Receita Federal</th>
                      <th className="text-gray-700 dark:text-neutral-200" style={{ padding: '10px', textAlign: 'center', fontWeight: 'bold' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Nome */}
                    <tr style={{
                      background: receitaFederalStatus.comparacao.nome?.divergente
                        ? '#dc3545' // Vermelho FORTE se divergente
                        : '#28a745', // Verde VIVO se OK
                      color: 'white',
                      borderBottom: '2px solid white'
                    }}>
                      <td style={{ padding: '12px', fontWeight: '600' }}>Nome</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.nome?.sistema || '-'}</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.nome?.receita_federal || '-'}</td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold', fontSize: '14px' }}>
                        {receitaFederalStatus.comparacao.nome?.divergente ? '⚠️ Diferente' : '✓ OK'}
                      </td>
                    </tr>
                    {/* CPF */}
                    <tr style={{
                      background: receitaFederalStatus.comparacao.cpf?.divergente
                        ? '#dc3545' // Vermelho FORTE se divergente
                        : '#28a745', // Verde VIVO se OK
                      color: 'white',
                      borderBottom: '2px solid white'
                    }}>
                      <td style={{ padding: '12px', fontWeight: '600' }}>CPF</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.cpf?.sistema || '-'}</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.cpf?.receita_federal || '-'}</td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold', fontSize: '14px' }}>
                        {receitaFederalStatus.comparacao.cpf?.divergente ? '⚠️ Diferente' : '✓ OK'}
                      </td>
                    </tr>
                    {/* Data de Nascimento */}
                    <tr style={{
                      background: receitaFederalStatus.comparacao.data_nascimento?.divergente
                        ? '#dc3545' // Vermelho FORTE se divergente
                        : '#28a745', // Verde VIVO se OK
                      color: 'white'
                    }}>
                      <td style={{ padding: '12px', fontWeight: '600' }}>Data Nascimento</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.data_nascimento?.sistema || '-'}</td>
                      <td style={{ padding: '12px', fontWeight: '500' }}>{receitaFederalStatus.comparacao.data_nascimento?.receita_federal || '-'}</td>
                      <td style={{ padding: '12px', textAlign: 'center', fontWeight: 'bold', fontSize: '14px' }}>
                        {receitaFederalStatus.comparacao.data_nascimento?.divergente ? '⚠️ Diferente' : '✓ OK'}
                      </td>
                    </tr>
                  </tbody>
                </table>
                <div className="text-gray-700 dark:text-neutral-300" style={{ marginTop: '10px', fontSize: '12px', fontStyle: 'italic', opacity: 0.9 }}>
                  ℹ️ Os dados da Receita Federal são prioritários e já foram aplicados automaticamente.
                </div>
              </div>
            )}
          </div>
        )}

        {loadingRequisicao && (
          <div className="flex items-center justify-center py-12">
            Buscando dados da requisição...
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white dark:bg-neutral-900 rounded-none p-0" noValidate>
          <div className="mb-7 pb-5 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
            <h3></h3>

            <div className="mb-4">
              <label>Código Requisição</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  name="codRequisicao"
                  value={formData.codRequisicao}
                  onChange={handleChange}
                  placeholder="Digite o codigo da requisicao (busca automatica)"
                  className="bg-white dark:bg-neutral-800 border-gray-300 dark:border-neutral-600 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-400"
                  style={{ width: '100%', fontSize: '16px', padding: '12px', paddingRight: loadingRequisicao ? '140px' : '12px' }}
                />
                {loadingRequisicao && (
                  <span style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', color: '#0ea5e9', fontSize: '14px', fontWeight: '500' }}>
                    Buscando...
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="mb-7 pb-5 border-b border-gray-200 last:border-b-0">
            <h3>Exames</h3>

            {resultadoConsolidadoFinal?.requisicoes?.[0]?.requisicao?.itens_exame &&
             Array.isArray(resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame) &&
             resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame.length > 0 && (
              <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md mb-4">
                <label className="text-sky-700 dark:text-sky-400" style={{fontWeight: '600', marginBottom: '8px'}}>
                  📋 Exames Extraídos pelo OCR
                </label>
                <div className="bg-white dark:bg-neutral-800 border-2 border-sky-200 dark:border-sky-700" style={{padding: '10px', borderRadius: '4px'}}>
                  {resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame.map((exame, idx) => (
                    <div key={idx} className="bg-sky-100 dark:bg-sky-900/30 text-sky-900 dark:text-sky-300" style={{
                      padding: '6px 10px',
                      margin: '4px 0',
                      borderRadius: '4px',
                      fontSize: '13px'
                    }}>
                      {idx + 1}. {typeof exame === 'object' ? (exame.descricao_ocr || exame.descricao || JSON.stringify(exame)) : exame}
                    </div>
                  ))}
                </div>
                <small style={{color: '#0369a1', display: 'block', marginTop: '8px'}}>
                  ⚠️ Atenção: Os IDs devem ser preenchidos automaticamente. Se não foram, clique no botão abaixo.
                </small>
                <button
                  type="button"
                  onClick={async () => {
                    const nomesExames = resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame.map(ex => {
                      if (typeof ex === 'object') {
                        return ex.descricao_ocr || ex.descricao || String(ex);
                      }
                      return String(ex);
                    });

                    console.log('[BUSCAR IDS MANUAL] Buscando IDs para:', nomesExames);

                    try {
                      const response = await apiFetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ nomes_exames: nomesExames })
                      });

                      const result = await response.json();
                      console.log('[BUSCAR IDS MANUAL] Resultado completo:', JSON.stringify(result, null, 2));

                      if (result.sucesso && result.resultados) {
                        const idsEncontrados = result.resultados
                          .filter(r => r.encontrado && r.idExame)
                          .map(r => r.idExame);

                        // Pegar os nomes dos exames para o campo "EXAMES CONVÊNIO"
                        const nomesExamesEncontrados = result.resultados
                          .filter(r => r.encontrado)
                          .map(r => r.nome_ocr || r.NomExame);

                        console.log('[BUSCAR IDS MANUAL] IDs encontrados:', idsEncontrados);
                        console.log('[BUSCAR IDS MANUAL] Nomes dos exames:', nomesExamesEncontrados);

                        if (idsEncontrados.length > 0) {
                          const idPrincipal = idsEncontrados[0].toString();
                          const examesString = nomesExamesEncontrados.join(', ');

                          console.log('[BUSCAR IDS MANUAL] Preenchendo campos:');
                          console.log('  - idExame:', idPrincipal);
                          console.log('  - examesConvenio:', examesString);

                          setFormData(prev => ({
                            ...prev,
                            // Campo EXAMES CONVÊNIO recebe os NOMES dos exames
                            examesConvenio: examesString,
                            // Campo ID EXAME PRINCIPAL recebe o primeiro ID
                            idExame: idPrincipal
                          }));

                          // Atualizar também no card do paciente
                          setPatientData(prev => ({
                            ...prev,
                            exams: examesString
                          }));

                          setMessage({
                            type: 'success',
                            text: `✓ ${idsEncontrados.length} exame(s) encontrado(s)! ID Principal: ${idPrincipal}`
                          });
                        } else {
                          setMessage({
                            type: 'warning',
                            text: '⚠️ Nenhum exame foi encontrado no banco de dados'
                          });
                        }
                      }
                    } catch (error) {
                      console.error('[BUSCAR IDS MANUAL] Erro:', error);
                      setMessage({
                        type: 'error',
                        text: `Erro ao buscar IDs: ${error.message}`
                      });
                    }
                  }}
                  style={{
                    marginTop: '10px',
                    padding: '8px 16px',
                    background: '#0ea5e9',
                    color: 'white',
                    border: 'none',
                    borderRadius: '5px',
                    fontSize: '12px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    width: '100%'
                  }}
                >
                  🔍 Buscar IDs dos Exames no Banco de Dados
                </button>
              </div>
            )}
          </div>

          {message && (
            <div className={`message message-${message.type}`} style={{ whiteSpace: 'pre-line' }}>
              {message.text}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-8 border-t-2 border-gray-200 dark:border-neutral-700">
            <button
              type="button"
              onClick={async () => {
                if (!formData.codRequisicao) {
                  setMessage({
                    type: 'error',
                    text: 'Digite um código de requisição primeiro'
                  });
                  return;
                }

                setLoading(true);
                setMessage({ type: 'info', text: '🔄 Iniciando análise automática...' });

                try {
                  // 1. Buscar requisição e capturar dados retornados
                  console.log('[ANÁLISE AUTO] Etapa 1: Buscando requisição...');
                  const response = await apiFetch(`${API_BASE_URL}/api/requisicao/${formData.codRequisicao}`);
                  const data = await response.json();

                  if (!response.ok || !data.sucesso) {
                    throw new Error(data.erro || 'Erro ao buscar requisição');
                  }

                  // Atualizar estados com os dados da requisição
                  setRequisicaoData(data.requisicao);
                  setImagens(data.imagens || []);
                  console.log(`[ANÁLISE AUTO] Requisição encontrada com ${data.imagens?.length || 0} imagens`);

                  // 2. Processar OCR de todas as imagens
                  console.log('[ANÁLISE AUTO] Etapa 2: Processando OCR das imagens...');
                  const imagensParaProcessar = data.imagens || [];
                  const dadosOCRColetados = []; // Array local para coletar dados (declarado aqui para estar acessível depois)

                  if (imagensParaProcessar.length > 0) {
                    setMessage({ type: 'info', text: `🔄 Analisando ${imagensParaProcessar.length} imagens com OCR...` });

                    // Limpar dados de OCR anteriores
                    setDadosOCRConsolidados([]);
                    setImagensProcessadas(new Set());

                    let sucessos = 0;
                    let erros = 0;

                    for (let i = 0; i < imagensParaProcessar.length; i++) {
                      const img = imagensParaProcessar[i];
                      console.log(`\n${'='.repeat(80)}`);
                      console.log(`[ANÁLISE AUTO] Processando imagem ${i + 1}/${imagensParaProcessar.length}`);
                      console.log(`[ANÁLISE AUTO] Nome: ${img.nome}`);
                      console.log(`[ANÁLISE AUTO] URL: ${img.url}`);
                      console.log(`${'='.repeat(80)}\n`);

                      setMessage({ type: 'info', text: `🔄 Processando ${i + 1}/${imagensParaProcessar.length}: ${img.nome}` });

                      try {
                        console.log(`[ANÁLISE AUTO] Enviando requisição OCR para: ${API_BASE_URL}/api/ocr/processar`);

                        // Retry com backoff exponencial para erro 429 (rate limit)
                        let tentativas = 0;
                        let maxTentativas = 3;
                        let ocrResponse = null;
                        let ocrResult = null;
                        let sucesso = false;

                        while (tentativas < maxTentativas && !sucesso) {
                          tentativas++;

                          if (tentativas > 1) {
                            const delayRetry = Math.pow(2, tentativas - 1) * 15000; // 15s, 30s, 60s (aumentado!)
                            console.log(`[ANÁLISE AUTO] 🔄 Tentativa ${tentativas}/${maxTentativas} - Aguardando ${delayRetry/1000}s antes de tentar novamente...`);
                            setMessage({ type: 'info', text: `⏳ Aguardando ${delayRetry/1000}s para retry (tentativa ${tentativas}/${maxTentativas})...` });
                            await new Promise(resolve => setTimeout(resolve, delayRetry));
                          }

                          try {
                            ocrResponse = await apiFetch(`${API_BASE_URL}/api/ocr/processar`, {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                imagemUrl: img.url,
                                imagemNome: img.nome
                              })
                            });

                            console.log(`[ANÁLISE AUTO] Status da resposta (tentativa ${tentativas}): ${ocrResponse.status}`);

                            ocrResult = await ocrResponse.json();
                            console.log(`[ANÁLISE AUTO] Resposta OCR (tentativa ${tentativas}):`, ocrResult);
                            if (ocrResult.erro) console.error(`[ANÁLISE AUTO] ERRO: ${ocrResult.erro}`);
                            if (ocrResult.traceback) console.error(`[ANÁLISE AUTO] TRACEBACK:\n${ocrResult.traceback}`);

                            // Verificar se foi erro 429 (rate limit)
                            if (ocrResponse.status === 500 && ocrResult.erro && ocrResult.erro.includes('429')) {
                              console.warn(`[ANÁLISE AUTO] ⚠ Rate limit (429) detectado na tentativa ${tentativas}`);
                              if (tentativas < maxTentativas) {
                                continue; // Tentar novamente
                              }
                            }

                            // Se chegou aqui e teve sucesso, marcar como sucesso
                            if (ocrResponse.ok && ocrResult.sucesso) {
                              sucesso = true;
                              const dadoImagem = {
                                imagem: img.nome,
                                timestamp: new Date().toISOString(),
                                dados: ocrResult.dados
                              };

                              // Adicionar ao array local
                              dadosOCRColetados.push(dadoImagem);

                              // Atualizar estados
                              setImagensProcessadas(prev => new Set([...prev, img.nome]));
                              setDadosOCRConsolidados(prev => [...prev, dadoImagem]);

                              sucessos++;
                              console.log(`[ANÁLISE AUTO] ✓ Imagem ${i + 1} processada com sucesso! (${sucessos} sucessos, ${erros} erros)`);
                              console.log(`[ANÁLISE AUTO] Total de dados coletados até agora: ${dadosOCRColetados.length}`);
                              break;
                            } else {
                              // Outro tipo de erro
                              if (tentativas >= maxTentativas) {
                                erros++;
                                console.warn(`[ANÁLISE AUTO] ⚠ Erro ao processar imagem ${i + 1} após ${maxTentativas} tentativas: ${ocrResult.erro || 'Erro desconhecido'}`);
                                console.warn(`[ANÁLISE AUTO] Detalhes do erro:`, ocrResult);
                              }
                            }
                          } catch (fetchError) {
                            console.error(`[ANÁLISE AUTO] ✗ Erro na requisição (tentativa ${tentativas}):`, fetchError);
                            if (tentativas >= maxTentativas) {
                              throw fetchError;
                            }
                          }
                        }
                      } catch (imgError) {
                        erros++;
                        console.error(`[ANÁLISE AUTO] ✗ Exceção na imagem ${i + 1}:`, imgError);
                        console.error(`[ANÁLISE AUTO] Stack trace:`, imgError.stack);
                      }

                      // Aguardar entre processamentos para evitar sobrecarga
                      console.log(`[ANÁLISE AUTO] Aguardando 10 segundos antes da próxima imagem...\n`);
                      await new Promise(resolve => setTimeout(resolve, 10000));
                    }

                    console.log(`\n${'='.repeat(80)}`);
                    console.log(`[ANÁLISE AUTO] RESUMO: ${sucessos} sucessos, ${erros} erros de ${imagensParaProcessar.length} imagens`);
                    console.log(`${'='.repeat(80)}\n`);
                  } else {
                    console.log('[ANÁLISE AUTO] ⚠ Nenhuma imagem encontrada para processar OCR');
                    setMessage({ type: 'warning', text: 'Nenhuma imagem encontrada para análise' });
                  }

                  // 3. Gerar JSON consolidado
                  console.log('[ANÁLISE AUTO] Etapa 3: Gerando JSON consolidado...');
                  console.log('[ANÁLISE AUTO] Dados coletados para consolidação:', dadosOCRColetados.length, 'imagens');
                  setMessage({ type: 'info', text: '🔄 Gerando JSON consolidado...' });
                  await new Promise(resolve => setTimeout(resolve, 1500));
                  await consolidarResultados(dadosOCRColetados);

                  setMessage({
                    type: 'success',
                    text: '✅ Análise automática concluída com sucesso!'
                  });
                } catch (error) {
                  console.error('[ANÁLISE AUTO] ✗ Erro:', error);
                  setMessage({
                    type: 'error',
                    text: `Erro na análise automática: ${error.message}`
                  });
                } finally {
                  setLoading(false);
                }
              }}
              className="px-10 py-4 bg-blue-600 hover:bg-blue-700 text-white border-0 rounded-lg text-base font-bold cursor-pointer transition-all hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={loading || loadingRequisicao || !formData.codRequisicao}
            >
              {loading ? 'Analisando...' : 'Iniciar Análise Automática'}
            </button>

            <button
              type="submit"
              className="px-10 py-4 bg-blue-600 hover:bg-blue-700 text-white border-0 rounded-lg text-base font-bold cursor-pointer transition-all hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              disabled={loading || loadingRequisicao}
            >
              {loading ? 'Salvando...' : 'Salvar Admissão'}
            </button>
          </div>
        </form>
          </>
        )}

        {/* Conteúdo da aba de Visualizar Imagens e Dados */}
        {abaPrincipal === 'visualizar' && (
          <div className="bg-white dark:bg-neutral-800 dark:shadow-lg dark:shadow-neutral-900/20" style={{
            borderRadius: '12px',
            padding: '30px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
          }}>
            <h2 className="text-emerald-600 dark:text-emerald-400" style={{
              margin: '0 0 25px 0',
              fontSize: '24px',
              fontWeight: '700',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <span></span> Visualizar Imagens e Dados do Paciente
            </h2>

            {/* Aviso de Campos Obrigatórios Faltantes */}
            {patientData && (() => {
              // Apenas campos REALMENTE obrigatórios para cadastro pela API
              const camposObrigatorios = [
                { campo: 'nome', label: 'Nome', valor: patientData.nome },
                { campo: 'dtaNasc', label: 'Data Nasc.', valor: patientData.dtaNasc },
                { campo: 'cpf', label: 'CPF', valor: patientData.cpf },
                { campo: 'sexo', label: 'Sexo', valor: patientData.sexo }
              ];

              const camposFaltantes = camposObrigatorios.filter(item => !item.valor || (typeof item.valor === 'string' && item.valor.trim() === ''));

              if (camposFaltantes.length > 0) {
                return (
                  <div style={{
                    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                    color: 'white',
                    padding: '20px 25px',
                    borderRadius: '12px',
                    marginBottom: '25px',
                    boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)',
                    border: '2px solid #b91c1c'
                  }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '15px'
                    }}>
                      <div style={{
                        fontSize: '32px',
                        lineHeight: '1'
                      }}>
                        ⚠️
                      </div>
                      <div style={{ flex: 1 }}>
                        <h3 style={{
                          margin: '0 0 12px 0',
                          fontSize: '18px',
                          fontWeight: '700',
                          letterSpacing: '0.5px'
                        }}>
                          ATENÇÃO: Dados Obrigatórios Não Preenchidos
                        </h3>
                        <p style={{
                          margin: '0 0 15px 0',
                          fontSize: '14px',
                          opacity: 0.95
                        }}>
                          Os seguintes campos são obrigatórios para salvar no APLIS:
                        </p>
                        <div style={{
                          background: 'rgba(255, 255, 255, 0.15)',
                          padding: '15px',
                          borderRadius: '8px',
                          backdropFilter: 'blur(10px)',
                          display: 'flex',
                          flexWrap: 'wrap',
                          gap: '8px'
                        }}>
                          {camposFaltantes.map((item, idx) => (
                            <span
                              key={idx}
                              style={{
                                background: '#7f1d1d',
                                padding: '8px 12px',
                                borderRadius: '6px',
                                fontSize: '13px',
                                fontWeight: '700',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                border: '1px solid rgba(255,255,255,0.2)'
                              }}
                            >
                              <span>❌</span>
                              <span>{item.label}</span>
                            </span>
                          ))}
                        </div>
                        <p style={{
                          margin: '15px 0 0 0',
                          fontSize: '13px',
                          opacity: 0.9,
                          fontWeight: '600'
                        }}>
                          💡 Preencha os campos faltantes na aba "Sistema Admissão com OCR" antes de salvar.
                        </p>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            })()}

            {/* Galeria de Imagens */}
            <div>
              <h3 className="text-emerald-600 dark:text-emerald-400" style={{
                margin: '0 0 20px 0',
                fontSize: '18px',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span></span> Imagens Carregadas ({imagens.length})
              </h3>

              {imagens.length === 0 ? (
                <div className="bg-gray-50 dark:bg-neutral-700 border-2 border-dashed border-gray-300 dark:border-neutral-600" style={{
                  textAlign: 'center',
                  padding: '60px 20px',
                  borderRadius: '12px'
                }}>
                  <div style={{ fontSize: '64px', marginBottom: '15px', opacity: 0.5 }}>🖼️</div>
                  <div className="text-gray-600 dark:text-neutral-300" style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
                    Nenhuma imagem carregada
                  </div>
                  <div className="text-gray-400 dark:text-neutral-500" style={{ fontSize: '14px' }}>
                    As imagens aparecerão aqui quando você processar uma requisição
                  </div>
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: '20px'
                }}>
                  {imagens.map((img, idx) => {
                    const isPDF = img.nome?.toUpperCase().endsWith('.PDF');
                    
                    // Debug: Log da imagem
                    console.log(`[IMAGEM ${idx}]`, {
                      nome: img.nome,
                      url: img.url,
                      tipo: img.tipo,
                      isPDF
                    });
                    
                    return (
                    <div
                      key={img.nome || idx}
                      style={{
                        background: 'white',
                        border: imagensProcessadas.has(img.nome) ? '2px solid #10b981' : '2px solid #e5e7eb',
                        borderRadius: '12px',
                        padding: '15px',
                        cursor: 'pointer',
                        transition: 'all 0.3s ease',
                        position: 'relative',
                        boxShadow: imagensProcessadas.has(img.nome) ? '0 4px 12px rgba(16, 185, 129, 0.2)' : '0 2px 4px rgba(0,0,0,0.05)'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = '#10b981';
                        e.currentTarget.style.boxShadow = '0 8px 20px rgba(16, 185, 129, 0.3)';
                        e.currentTarget.style.transform = 'translateY(-5px)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = imagensProcessadas.has(img.nome) ? '#10b981' : '#e5e7eb';
                        e.currentTarget.style.boxShadow = imagensProcessadas.has(img.nome) ? '0 4px 12px rgba(16, 185, 129, 0.2)' : '0 2px 4px rgba(0,0,0,0.05)';
                        e.currentTarget.style.transform = 'translateY(0)';
                      }}
                    >
                      {imagensProcessadas.has(img.nome) && (
                        <div style={{
                          position: 'absolute',
                          top: '10px',
                          right: '10px',
                          background: '#10b981',
                          color: 'white',
                          padding: '4px 8px',
                          borderRadius: '6px',
                          fontSize: '11px',
                          fontWeight: '700',
                          boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                        }}>
                          ✓ OCR Processado
                        </div>
                      )}

                      <div
                        onClick={() => setImagemSelecionada(img)}
                        style={{ position: 'relative' }}
                      >
                        {isPDF ? (
                          <div style={{
                            width: '100%',
                            height: '200px',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                            borderRadius: '8px',
                            marginBottom: '12px',
                            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)'
                          }}>
                            <div style={{
                              fontSize: '72px',
                              marginBottom: '12px',
                              filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))'
                            }}>
                              📄
                            </div>
                            <div style={{
                              color: 'white',
                              fontSize: '18px',
                              fontWeight: '700',
                              textShadow: '0 2px 4px rgba(0,0,0,0.3)',
                              letterSpacing: '1px'
                            }}>
                              DOCUMENTO PDF
                            </div>
                            <div style={{
                              color: 'rgba(255,255,255,0.9)',
                              fontSize: '12px',
                              marginTop: '8px',
                              textShadow: '0 1px 2px rgba(0,0,0,0.2)'
                            }}>
                              Clique para visualizar
                            </div>
                          </div>
                        ) : (
                          <img
                            src={img.url}
                            alt={img.nome}
                            style={{
                              width: '100%',
                              height: '200px',
                              objectFit: 'cover',
                              borderRadius: '8px',
                              marginBottom: '12px'
                            }}
                            onError={(e) => {
                              console.error('Erro ao carregar imagem:', img.nome, img.url);
                              e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EErro ao carregar%3C/text%3E%3C/svg%3E';
                            }}
                          />
                        )}
                      </div>

                      <div style={{ marginBottom: '12px' }}>
                        <div className="text-emerald-600 dark:text-emerald-400" style={{
                          fontSize: '13px',
                          fontWeight: '700',
                          marginBottom: '4px'
                        }}>
                          TIPO: {img.tipo}
                        </div>
                        <div className="text-gray-600 dark:text-neutral-300" style={{
                          fontSize: '12px',
                          wordBreak: 'break-all'
                        }}>
                          {img.nome}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          processarOCR(img.url, img.nome, false);
                        }}
                        disabled={loadingOCR || imagensProcessadas.has(img.nome)}
                        style={{
                          width: '100%',
                          padding: '10px',
                          background: imagensProcessadas.has(img.nome)
                            ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)'
                            : 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                          color: 'white',
                          border: 'none',
                          borderRadius: '8px',
                          fontSize: '13px',
                          fontWeight: '700',
                          cursor: (loadingOCR || imagensProcessadas.has(img.nome)) ? 'not-allowed' : 'pointer',
                          opacity: (loadingOCR || imagensProcessadas.has(img.nome)) ? 0.7 : 1,
                          transition: 'all 0.2s ease',
                          boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                        }}
                        onMouseEnter={(e) => {
                          if (!loadingOCR && !imagensProcessadas.has(img.nome)) {
                            e.currentTarget.style.transform = 'scale(1.05)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'scale(1)';
                        }}
                      >
                        {imagensProcessadas.has(img.nome) ? '✓ Processado' : loadingOCR ? '⏳ Processando...' : '🔍 PROCESSAR OCR'}
                      </button>
                    </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modal para visualizar imagem ou PDF */}
      {imagemSelecionada && (
        <div className="fixed inset-0 w-screen h-screen bg-black/90 dark:bg-black/95 flex items-center justify-center z-[9999] animate-fadeIn" onClick={fecharModal}>
          <div className="relative max-w-[95vw] max-h-[95vh] bg-white dark:bg-neutral-800 rounded-2xl overflow-hidden shadow-[0_16px_48px_rgba(0,0,0,0.5)] dark:shadow-[0_16px_48px_rgba(0,0,0,0.9)] animate-slideUp flex flex-col" onClick={(e) => e.stopPropagation()}>
            <button className="fixed top-6 right-6 bg-black/70 text-white border-0 w-10 h-10 rounded-full text-2xl cursor-pointer flex items-center justify-center transition-all z-[103] leading-none hover:bg-black/90 hover:rotate-90" onClick={fecharModal}>&times;</button>

            {/* Botão Editar Fixo no Topo */}
            {patientData && !modoEdicaoModal && (
              <button
                className="fixed top-6 right-[88px] bg-primary text-white border-0 px-5 py-2.5 rounded-lg text-sm font-semibold cursor-pointer transition-all flex items-center gap-1.5 z-[102] shadow-[0_2px_12px_rgba(102,126,234,0.4)] dark:shadow-[0_2px_12px_rgba(102,126,234,0.6)] h-10 hover:bg-primary-dark hover:-translate-y-0.5 hover:shadow-[0_4px_16px_rgba(102,126,234,0.5)]"
                onClick={iniciarEdicaoModal}
                title="Editar dados"
              >
                ✏️ Editar
              </button>
            )}

            {/* Botões Salvar/Cancelar Fixos no Topo */}
            {modoEdicaoModal && (
              <div className="fixed top-6 right-[88px] flex gap-2.5 z-[102] items-center">
                <button
                  className="bg-gray-600 dark:bg-neutral-600 text-white border-0 px-5 py-2.5 rounded-lg text-sm font-semibold cursor-pointer transition-all shadow-[0_2px_12px_rgba(107,114,128,0.4)] dark:shadow-[0_2px_12px_rgba(82,82,91,0.6)] h-10 hover:bg-gray-700 dark:hover:bg-neutral-700 hover:-translate-y-0.5 hover:shadow-[0_4px_16px_rgba(107,114,128,0.5)] disabled:opacity-60 disabled:cursor-not-allowed"
                  onClick={cancelarEdicaoModal}
                  disabled={salvandoDados}
                >
                  Cancelar
                </button>
                <button
                  className="bg-success text-white border-0 px-5 py-2.5 rounded-lg text-sm font-semibold cursor-pointer transition-all shadow-[0_2px_12px_rgba(16,185,129,0.4)] dark:shadow-[0_2px_12px_rgba(16,185,129,0.6)] h-10 hover:bg-success-dark hover:-translate-y-0.5 hover:shadow-[0_4px_16px_rgba(16,185,129,0.5)] disabled:opacity-60 disabled:cursor-not-allowed"
                  onClick={salvarAlteracoesModal}
                  disabled={salvandoDados}
                >
                  {salvandoDados ? 'Salvando...' : '✓ Salvar'}
                </button>
              </div>
            )}

            {/* Container principal: Imagem + Dados do Paciente */}
            <div className="flex gap-0 h-full overflow-hidden">
              {/* Coluna da Imagem */}
              <div className="flex-1 flex flex-col min-w-0 border-r-2 border-gray-200 dark:border-neutral-700">
                {/* Controles de Zoom e Processar OCR */}
                <div className="p-5 pr-20 pl-5 bg-black/5 dark:bg-neutral-900/50 border-b-2 border-gray-200 dark:border-neutral-700 flex justify-between items-center gap-7.5 flex-nowrap relative z-[1]">
                  {/* Controles de Zoom */}
                  {!imagemSelecionada.nome.toUpperCase().endsWith('.PDF') && (
                    <div className="flex gap-2.5 bg-black/70 px-4 py-2.5 rounded-[30px] backdrop-blur-[10px] flex-shrink-0">
                      <button onClick={zoomOut} title="Diminuir zoom">-</button>
                      <button onClick={resetZoom} title="Resetar zoom">{Math.round(zoomLevel * 100)}%</button>
                      <button onClick={zoomIn} title="Aumentar zoom">+</button>
                    </div>
                  )}

                  {/* Botão Processar OCR */}
                  <button
                    className="bg-primary text-white border-0 px-7 py-3 rounded-lg text-sm font-semibold cursor-pointer transition-all shadow-[0_2px_8px_rgba(0,0,0,0.15)] hover:bg-primary-dark hover:-translate-y-0.5 hover:shadow-[0_4px_12px_rgba(0,0,0,0.25)] disabled:opacity-60 disabled:cursor-not-allowed"
                    onClick={() => {
                      processarOCR(imagemSelecionada.url, imagemSelecionada.nome);
                      fecharModal();
                    }}
                    disabled={loadingOCR || imagensProcessadas.has(imagemSelecionada.nome)}
                  >
                    {imagensProcessadas.has(imagemSelecionada.nome)
                      ? '✓ Já Processado'
                      : (loadingOCR ? 'Processando OCR...' : 'Processar OCR')}
                  </button>
                </div>

                <div className="image-container" style={{ overflow: 'auto', maxHeight: '70vh' }}>
                  {imagemSelecionada.nome.toUpperCase().endsWith('.PDF') ? (
                    <iframe
                      src={imagemSelecionada.url}
                      title={imagemSelecionada.nome}
                      className="w-[90vw] h-[75vh] border-0 block"
                    />
                  ) : (
                    <img
                      src={imagemSelecionada.url}
                      alt={imagemSelecionada.nome}
                      style={{
                        transform: `scale(${zoomLevel})`,
                        transformOrigin: 'top left',
                        transition: 'transform 0.2s ease',
                        cursor: zoomLevel > 1 ? 'move' : 'default'
                      }}
                    />
                  )}
                </div>

                <div className="p-4 bg-gray-50 dark:bg-neutral-900 border-t border-gray-200 dark:border-neutral-700 text-center">
                  <p className="text-gray-700 dark:text-neutral-300">{imagemSelecionada.nome}</p>
                </div>
              </div>

              {/* Coluna dos Dados do Paciente */}
              {patientData && (
                <div className="w-[350px] bg-gray-50 dark:bg-neutral-900 overflow-y-auto flex-shrink-0 relative">
                  <div className="pt-20 px-6 pb-6">
                    <h3 className="text-base font-bold text-gray-900 dark:text-neutral-100 my-0 mb-6 pb-3 border-b-[3px] border-primary uppercase tracking-wide">DADOS DO PACIENTE</h3>
                    
                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">NOME COMPLETO</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 dark:border-neutral-600 rounded-md text-sm font-medium text-gray-900 dark:text-neutral-100 transition-all bg-white dark:bg-neutral-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.nome || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, nome: e.target.value }))}
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-neutral-200">{patientData.name || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">DATA DE NASCIMENTO</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="date"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 dark:border-neutral-600 rounded-md text-sm font-medium text-gray-900 dark:text-neutral-100 transition-all bg-white dark:bg-neutral-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={converterDataParaISO(dadosEditaveis?.dataNascimento || '')}
                          onChange={(e) => {
                            const data = e.target.value;
                            const [ano, mes, dia] = data.split('-');
                            const dataFormatada = `${dia}/${mes}/${ano}`;
                            setDadosEditaveis(prev => ({ ...prev, dataNascimento: dataFormatada }));
                          }}
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-neutral-200">{patientData.birthDate || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">IDADE</strong>
                      <span className="text-gray-900 dark:text-neutral-200">{patientData.age || 'Não informado'}</span>
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">CPF</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 dark:border-neutral-600 rounded-md text-sm font-medium text-gray-900 dark:text-neutral-100 transition-all bg-white dark:bg-neutral-800 focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.cpf || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, cpf: e.target.value }))}
                        />
                      ) : (
                        <div>
                          <span className="text-gray-900 dark:text-neutral-200">{patientData.cpf || 'Não informado'}</span>

                          {/* 🆕 BOTÃO VALIDAR CPF */}
                          {patientData.cpf && (
                            <button
                              onClick={validarCPFManualmente}
                              style={{
                                marginTop: '10px',
                                width: '100%',
                                padding: '10px 16px',
                                background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                                color: 'white',
                                border: 'none',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                fontWeight: '600',
                                fontSize: '14px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px',
                                boxShadow: '0 4px 12px rgba(16, 185, 129, 0.3)',
                                transition: 'all 0.3s ease'
                              }}
                              onMouseOver={(e) => {
                                e.currentTarget.style.transform = 'translateY(-2px)';
                                e.currentTarget.style.boxShadow = '0 6px 16px rgba(16, 185, 129, 0.4)';
                              }}
                              onMouseOut={(e) => {
                                e.currentTarget.style.transform = 'translateY(0)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.3)';
                              }}
                            >
                              <span style={{ fontSize: '18px' }}>✓</span>
                              Validar CPF na Receita Federal
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">RG</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.rg || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, rg: e.target.value }))}
                        />
                      ) : (
                        <span className="text-gray-900 dark:text-neutral-200">{patientData.rg || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 dark:border-neutral-700 last:border-b-0">
                      <strong className="text-gray-700 dark:text-neutral-300">TELEFONE</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.telefone || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, telefone: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.phone || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>E-MAIL</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="email"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.email || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, email: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.email || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>Nº CARTEIRINHA</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosEditaveis?.carteirinha || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, carteirinha: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.insuranceCardNumber || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>ENDEREÇO</strong>
                      {modoEdicaoModal ? (
                        <textarea
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          rows="3"
                          value={dadosEditaveis?.endereco || ''}
                          onChange={(e) => setDadosEditaveis(prev => ({ ...prev, endereco: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.address || 'Não informado'}</span>
                      )}
                    </div>

                    <h3 className="text-base font-bold text-gray-900 dark:text-neutral-100 my-0 mb-6 pb-3 border-b-[3px] border-primary uppercase tracking-wide" style={{ marginTop: '32px' }}>DADOS DA REQUISIÇÃO</h3>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>Nº REQUISIÇÃO</strong>
                      <span>{patientData.recordNumber || 'Não informado'}</span>
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>DATA DA COLETA</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="date"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={converterDataParaISO(dadosRequisicaoEditaveis?.dataColeta || '')}
                          onChange={(e) => {
                            const data = e.target.value;
                            const [ano, mes, dia] = data.split('-');
                            const dataFormatada = `${dia}/${mes}/${ano}`;
                            setDadosRequisicaoEditaveis(prev => ({ ...prev, dataColeta: dataFormatada }));
                          }}
                        />
                      ) : (
                        <span>{patientData.collectionDate || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>CONVÊNIO</strong>
                      {modoEdicaoModal ? (
                        <ConvenioSelect
                          value={dadosRequisicaoEditaveis?.convenio || ''}
                          onChange={(selectedConvenio) => setDadosRequisicaoEditaveis(prev => ({ ...prev, convenio: selectedConvenio?.nome || '' }))}
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                        />
                      ) : (
                        <span>{patientData.insurance || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>ORIGEM</strong>
                      {modoEdicaoModal ? (
                        <LocalOrigemSelect
                          value={dadosRequisicaoEditaveis?.origem || ''}
                          onChange={(selectedOrigem) => setDadosRequisicaoEditaveis(prev => ({ ...prev, origem: selectedOrigem?.nome || '' }))}
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                        />
                      ) : (
                        <span>{patientData.origin || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>FONTE PAGADORA</strong>
                      {modoEdicaoModal ? (
                        <FontePagadoraSelect
                          value={dadosRequisicaoEditaveis?.fontePagadora || ''}
                          onChange={(selectedFonte) => {
                            setDadosRequisicaoEditaveis(prev => ({ ...prev, fontePagadora: selectedFonte?.nome || '' }));
                            if (selectedFonte?.id) {
                              setFormData(prev => ({ ...prev, idFontePagadora: selectedFonte.id.toString() }));
                            }
                          }}
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                        />
                      ) : (
                        <span>{patientData.payingSource || 'Particular'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>MÉDICO SOLICITANTE</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosRequisicaoEditaveis?.medico || ''}
                          onChange={(e) => setDadosRequisicaoEditaveis(prev => ({ ...prev, medico: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.doctorName || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>CRM</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosRequisicaoEditaveis?.crm || ''}
                          onChange={(e) => setDadosRequisicaoEditaveis(prev => ({ ...prev, crm: e.target.value }))}
                        />
                      ) : (
                        <span>{patientData.doctorCRM || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>Nº GUIA</strong>
                      {modoEdicaoModal ? (
                        <input
                          type="text"
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          value={dadosRequisicaoEditaveis?.numGuia || ''}
                          onChange={(e) => setDadosRequisicaoEditaveis(prev => ({ ...prev, numGuia: e.target.value }))}
                        />
                      ) : (
                        <span>{requisicaoData?.requisicao?.numGuia || 'Não informado'}</span>
                      )}
                    </div>

                    <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                      <strong>DADOS CLÍNICOS</strong>
                      {modoEdicaoModal ? (
                        <textarea
                          className="w-full p-2.5 px-3 border-2 border-gray-300 rounded-md text-sm font-medium text-gray-900 transition-all bg-white focus:outline-none focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)]"
                          rows="4"
                          value={dadosRequisicaoEditaveis?.dadosClinicos || ''}
                          onChange={(e) => setDadosRequisicaoEditaveis(prev => ({ ...prev, dadosClinicos: e.target.value }))}
                        />
                      ) : (
                        <span style={{ whiteSpace: 'pre-wrap' }}>{requisicaoData?.requisicao?.dadosClinicos || 'Não informado'}</span>
                      )}
                    </div>

                    {requisicaoData?.exames && requisicaoData.exames.length > 0 && (
                      <div className="mb-5 pb-4 border-b border-gray-200 last:border-b-0">
                        <strong>EXAMES SOLICITADOS</strong>
                        <div style={{ marginTop: '8px' }}>
                          {requisicaoData.exames.map((exame, index) => (
                            <div key={index} style={{ 
                              padding: '8px 12px', 
                              background: 'white',
                              borderRadius: '6px',
                              marginBottom: '6px',
                              fontSize: '13px',
                              border: '1px solid #e0e0e0'
                            }}>
                              {exame.nome || exame.descricao || 'Exame não especificado'}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdmissionView;
