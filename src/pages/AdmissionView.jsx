import React, { useState, useEffect } from 'react';
import PatientCard from '../components/PatientCard';
import '../styles/AdmissionView.css';
import { API_BASE_URL } from '../config';

const AdmissionView = () => {
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
    dadosClinicos: ''
  });

  const [patientData, setPatientData] = useState(null);
  const [requisicaoData, setRequisicaoData] = useState(null);

  // Buscar dados da requisição quando código é alterado
  const buscarRequisicao = async (codRequisicao) => {
    if (!codRequisicao || codRequisicao.length < 10) return;

    setLoadingRequisicao(true);
    setMessage(null);

    // LIMPAR ESTADOS ANTERIORES
    setResultadoConsolidadoFinal(null);
    setDadosOCRConsolidados([]);
    setImagensProcessadas(new Set());

    try {
      const response = await fetch(`${API_BASE_URL}/api/requisicao/${codRequisicao}`);
      const data = await response.json();

      if (response.ok) {
        // Atualizar dados do paciente para exibir no card lateral
        if (data.paciente) {
          const idade = calcularIdade(data.paciente.dtaNasc);
          setPatientData({
            name: data.paciente.nome,
            age: `${idade} anos`,
            birthDate: formatarData(data.paciente.dtaNasc),
            recordNumber: data.requisicao.codRequisicao,
            origin: data.localOrigem?.nome || 'Não informado',
            payingSource: data.fontePagadora?.nome || 'Não informado',
            insurance: data.convenio?.nome || 'Não informado',
            doctorName: data.medico?.nome || 'Não informado',
            doctorCRM: data.medico?.crm ? `CRM: ${data.medico.crm}/${data.medico.uf}` : 'Não informado',
            collectionDate: formatarData(data.requisicao.dtaColeta),
            statusText: 'Em andamento',
            status: 'in-progress',
            cpf: data.paciente.cpf,
            rg: data.paciente.rg,
            phone: data.paciente.telCelular,
            address: formatarEndereco(data.paciente.endereco)
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

          return {
            ...prev,
            codRequisicao: data.requisicao.codRequisicao,
            dtaColeta: dataColeta,
            idPaciente: data.paciente.idPaciente?.toString() || prev.idPaciente || '',
            idConvenio: data.requisicao.idConvenio?.toString() || prev.idConvenio || '',
            idLocalOrigem: data.requisicao.idLocalOrigem?.toString() || prev.idLocalOrigem || '1',
            idFontePagadora: data.requisicao.idFontePagadora?.toString() || prev.idFontePagadora || '',
            idMedico: data.requisicao.idMedico?.toString() || prev.idMedico || '',
            numGuia: data.requisicao.numGuia || prev.numGuia || '',
            dadosClinicos: data.requisicao.dadosClinicos || prev.dadosClinicos || ''
            // examesConvenio e idExame serão preenchidos pelo OCR depois
          };
        });

        // Armazenar dados completos da requisição
        setRequisicaoData(data);

        // SEMPRE gerar JSON em topografia logo após carregar os dados
        console.log('[TOPOGRAFIA] Gerando visualização em topografia dos dados carregados');
        setTimeout(() => {
          consolidarResultados();
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

  // Debounce para buscar requisição
  useEffect(() => {
    const timer = setTimeout(() => {
      if (formData.codRequisicao) {
        buscarRequisicao(formData.codRequisicao);
      }
    }, 800); // Aguarda 800ms após parar de digitar

    return () => clearTimeout(timer);
  }, [formData.codRequisicao]);

  // Processar OCR automaticamente quando imagens carregarem
  useEffect(() => {
    if (imagens.length > 0) {
      console.log(`Processando OCR automaticamente para ${imagens.length} imagens...`);

      // Processar TODAS as imagens incluindo PDFs
      const imagensValidas = imagens;

      console.log(`${imagensValidas.length} arquivos para processar OCR (incluindo PDFs)`);

      // Processar cada imagem com um delay para não sobrecarregar
      imagensValidas.forEach((img, index) => {
        setTimeout(() => {
          // Verificar se não foi processada ainda
          if (!imagensProcessadas.has(img.nome)) {
            console.log(`Auto-processando imagem ${index + 1}/${imagensValidas.length}: ${img.nome}`);
            processarOCR(img.url, img.nome, true); // true = autoProcessamento
          }
        }, index * 3000); // Delay de 3 segundos entre cada imagem
      });
    }
  }, [imagens]);

  // Consolidar resultados quando TODAS as imagens forem processadas
  useEffect(() => {
    if (imagens.length > 0 && dadosOCRConsolidados.length === imagens.length && requisicaoData) {
      console.log('[CONSOLIDAR] Todas as imagens processadas, consolidando resultados...');
      consolidarResultados();
    }
  }, [dadosOCRConsolidados.length, imagens.length]);

  // Função para preencher formulário com dados do OCR
  const preencherFormularioComOCR = async (resultadoConsolidado) => {
    if (!resultadoConsolidado || !resultadoConsolidado.requisicoes || resultadoConsolidado.requisicoes.length === 0) {
      console.log('[PREENCHER] Nenhum dado para preencher');
      return;
    }

    const req = resultadoConsolidado.requisicoes[0];
    let camposPreenchidos = [];

    console.log('[PREENCHER] Iniciando preenchimento automático do formulário...');
    console.log('[PREENCHER] Dados OCR recebidos:', JSON.stringify(req, null, 2));
    console.log('[PREENCHER] FormData atual:', formData);

    // Criar objeto de atualização APENAS com campos do OCR
    const atualizacoesOCR = {};

    // Código da requisição do OCR (se não estiver preenchido)
    if (req.comentarios_gerais?.requisicao_entrada && !formData.codRequisicao) {
      atualizacoesOCR.codRequisicao = req.comentarios_gerais.requisicao_entrada;
      camposPreenchidos.push('Código da Requisição (OCR)');
      console.log('[PREENCHER] ✓ Código da requisição:', req.comentarios_gerais.requisicao_entrada);
    }

    // Data de coleta do OCR (sobrescreve API se existir)
    if (req.requisicao?.dtaColeta?.valor) {
      atualizacoesOCR.dtaColeta = req.requisicao.dtaColeta.valor;
      camposPreenchidos.push('Data de Coleta (OCR)');
      console.log('[PREENCHER] ✓ Data de coleta:', req.requisicao.dtaColeta.valor);
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

    // Exames - BUSCAR IDS AUTOMATICAMENTE
    console.log('[PREENCHER] Verificando itens_exame...');
    console.log('[PREENCHER] req.requisicao:', req.requisicao);
    console.log('[PREENCHER] req.requisicao.itens_exame:', req.requisicao?.itens_exame);

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
        const responseBusca = await fetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
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

          // Pegar NOMES dos exames para o campo "EXAMES CONVÊNIO"
          const nomesExamesEncontrados = resultBusca.resultados
            .filter(r => r.encontrado)
            .map(r => r.nome_ocr || r.NomExame);

          console.log('[PREENCHER] ✓ IDs filtrados:', idsEncontrados);
          console.log('[PREENCHER] ✓ Nomes dos exames:', nomesExamesEncontrados);

          if (idsEncontrados.length > 0) {
            // Campo EXAMES CONVÊNIO recebe os NOMES dos exames
            atualizacoesOCR.examesConvenio = nomesExamesEncontrados.join(', ');
            camposPreenchidos.push(`${nomesExamesEncontrados.length} exame(s)`);
            console.log('[PREENCHER] ✓ Nomes dos exames para campo EXAMES CONVÊNIO:', nomesExamesEncontrados.join(', '));

            // Usar o primeiro exame como idExame principal
            atualizacoesOCR.idExame = idsEncontrados[0].toString();
            camposPreenchidos.push('ID Exame Principal');
            console.log('[PREENCHER] ✓ ID Exame Principal:', idsEncontrados[0]);

            // Mostrar quais não foram encontrados
            const naoEncontrados = resultBusca.resultados
              .filter(r => !r.encontrado)
              .map(r => r.nome_ocr);

            if (naoEncontrados.length > 0) {
              console.warn('[PREENCHER] ⚠️ Exames não encontrados:', naoEncontrados.join(', '));
            }
          } else {
            console.warn('[PREENCHER] ⚠️ Nenhum exame foi encontrado no banco de dados');
          }
        }
      } catch (error) {
        console.error('[PREENCHER] Erro ao buscar IDs dos exames:', error);
      }
    }

    // Atualizar formulário - mesclar com valores existentes
    setFormData(prev => ({
      ...prev,
      ...atualizacoesOCR
    }));

    // Atualizar dados do paciente no card lateral com dados do OCR
    if (req.paciente) {
      console.log('[PREENCHER] 👤 Atualizando dados do paciente no card...');
      console.log('[PREENCHER] 🔍 Objeto paciente completo:', JSON.stringify(req.paciente, null, 2));

      const dadosPacienteOCR = {};

      // Nome do paciente (aceita múltiplas variações)
      const nome = req.paciente.NomPaciente?.valor || req.paciente.nome?.valor || req.paciente.NomePaciente?.valor;
      if (nome) {
        dadosPacienteOCR.name = nome;
        console.log('[PREENCHER] ✓ Nome:', nome);
      } else {
        console.log('[PREENCHER] ⚠️ Nome não encontrado. Campos disponíveis:', Object.keys(req.paciente));
      }

      // Data de nascimento e idade (aceita múltiplas variações)
      const dataNasc = req.paciente.DtaNasc?.valor || req.paciente.DtaNascimento?.valor || req.paciente.dataNascimento?.valor;
      if (dataNasc) {
        const idade = calcularIdade(dataNasc);
        dadosPacienteOCR.age = `${idade} anos`;
        dadosPacienteOCR.birthDate = formatarData(dataNasc);
        console.log('[PREENCHER] ✓ Data de nascimento:', dataNasc, `(${idade} anos)`);
      } else {
        console.log('[PREENCHER] ⚠️ Data de nascimento não encontrada');
      }

      // CPF (aceita múltiplas variações)
      const cpf = req.paciente.NumCPF?.valor || req.paciente.cpf?.valor || req.paciente.CPF?.valor;
      if (cpf) {
        dadosPacienteOCR.cpf = cpf;
        console.log('[PREENCHER] ✓ CPF:', cpf);
      } else {
        console.log('[PREENCHER] ⚠️ CPF não encontrado');
      }

      // RG (aceita múltiplas variações)
      const rg = req.paciente.NumRG?.valor || req.paciente.rg?.valor || req.paciente.RG?.valor || req.paciente.RGNumero?.valor;
      if (rg) {
        dadosPacienteOCR.rg = rg;
        console.log('[PREENCHER] ✓ RG:', rg);
      } else {
        console.log('[PREENCHER] ⚠️ RG não encontrado');
      }

      // Telefone (aceita múltiplas variações)
      const telefone = req.paciente.TelCelular?.valor || req.paciente.telefone?.valor || req.paciente.celular?.valor;
      if (telefone) {
        dadosPacienteOCR.phone = telefone;
        console.log('[PREENCHER] ✓ Telefone:', telefone);
      } else {
        console.log('[PREENCHER] ⚠️ Telefone não encontrado');
      }

      // Endereço (aceita múltiplas variações)
      const endereco = req.paciente.DscEndereco?.valor || req.paciente.endereco?.valor || req.paciente.Endereco?.valor;
      if (endereco) {
        dadosPacienteOCR.address = endereco;
        console.log('[PREENCHER] ✓ Endereço:', endereco);
      } else {
        console.log('[PREENCHER] ⚠️ Endereço não encontrado');
      }

      // Número da requisição (do OCR ou já preenchido)
      if (req.comentarios_gerais?.requisicao_entrada) {
        dadosPacienteOCR.recordNumber = req.comentarios_gerais.requisicao_entrada;
      }

      // Data de coleta
      if (req.requisicao?.dtaColeta?.valor) {
        dadosPacienteOCR.collectionDate = formatarData(req.requisicao.dtaColeta.valor);
      }

      // Status padrão para OCR
      dadosPacienteOCR.statusText = 'Dados extraídos por OCR';
      dadosPacienteOCR.status = 'in-progress';

      // Mesclar com dados existentes (se já tiver dados da API, mantém eles)
      setPatientData(prev => ({
        ...prev,
        ...dadosPacienteOCR
      }));

      console.log('[PREENCHER] ✓ Card do paciente atualizado com sucesso!');
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
      setMessage({
        type: 'info',
        text: 'OCR processado, mas nenhum campo adicional foi preenchido.'
      });
    }
  };

  // Função para consolidar resultados
  const consolidarResultados = async () => {
    try {
      console.log('[CONSOLIDAR] Iniciando consolidação...');
      console.log('[CONSOLIDAR] Dados OCR coletados:', dadosOCRConsolidados);
      console.log('[CONSOLIDAR] Quantidade de imagens processadas:', dadosOCRConsolidados.length);
      console.log('[CONSOLIDAR] Dados da API (requisicaoData):', requisicaoData);
      console.log('[CONSOLIDAR] Tipo de requisicaoData:', typeof requisicaoData);
      console.log('[CONSOLIDAR] É array?', Array.isArray(requisicaoData));

      // Garantir que dados_api seja um objeto válido
      let dadosParaEnviar = requisicaoData;
      if (Array.isArray(requisicaoData)) {
        console.warn('[CONSOLIDAR] ATENÇÃO: requisicaoData é um array, convertendo...');
        dadosParaEnviar = requisicaoData[0] || {};
      }

      const response = await fetch(`${API_BASE_URL}/api/consolidar-resultados`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          resultados_ocr: dadosOCRConsolidados,
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

        // PREENCHER FORMULÁRIO COM DADOS EXTRAÍDOS - AGUARDAR busca de IDs
        await preencherFormularioComOCR(result.resultado);

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

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const dados = {
        ...formData,
        idLaboratorio: parseInt(formData.idLaboratorio),
        idUnidade: parseInt(formData.idUnidade),
        idPaciente: parseInt(formData.idPaciente),
        idConvenio: parseInt(formData.idConvenio),
        idLocalOrigem: parseInt(formData.idLocalOrigem),
        idFontePagadora: parseInt(formData.idFontePagadora),
        idMedico: parseInt(formData.idMedico),
        idExame: parseInt(formData.idExame),
        examesConvenio: formData.examesConvenio.split(',').map(e => parseInt(e.trim()))
      };

      if (!dados.codRequisicao) {
        delete dados.codRequisicao;
      }

      const response = await fetch(`${API_BASE_URL}/api/admissao/salvar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
      });

      const result = await response.json();

      if (result.sucesso === 1) {
        setMessage({
          type: 'success',
          text: `Admissão salva com sucesso! Código: ${result.codRequisicao}`
        });

        // Atualizar código da requisição se foi criada uma nova
        if (!formData.codRequisicao && result.codRequisicao) {
          setFormData(prev => ({
            ...prev,
            codRequisicao: result.codRequisicao
          }));
        }
      } else {
        setMessage({
          type: 'error',
          text: result.erro || 'Erro ao salvar admissão'
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

      const response = await fetch(`${API_BASE_URL}/api/admissao/validar`, {
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
    if (!dtaNasc) return 0;
    const hoje = new Date();
    const nascimento = new Date(dtaNasc);
    let idade = hoje.getFullYear() - nascimento.getFullYear();
    const mes = hoje.getMonth() - nascimento.getMonth();
    if (mes < 0 || (mes === 0 && hoje.getDate() < nascimento.getDate())) {
      idade--;
    }
    return idade;
  };

  const formatarData = (data) => {
    if (!data) return '';
    const d = new Date(data);
    return d.toLocaleDateString('pt-BR');
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
      const response = await fetch(`${API_BASE_URL}/api/ocr/processar`, {
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

          if (!autoProcessamento) {
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
    setMessage({
      type: 'success',
      text: '✓ Dados do paciente atualizados com sucesso!'
    });
  };

  return (
    <div className="medical-system-layout">
      <PatientCard patient={patientData} onPatientUpdate={handlePatientUpdate} />

      <div className="admission-container">
        <div className="admission-header">
          <h1>Sistema Admissão com OCR</h1>
          <span className="badge badge-admission">OCR ATIVO</span>
        </div>

        {loadingRequisicao && (
          <div className="loading-indicator">
            Buscando dados da requisição...
          </div>
        )}

        <form onSubmit={handleSubmit} className="admission-form">
          <div className="form-section">
            <h3>Dados da Requisição</h3>

            <div className="form-group">
              <label>Código Requisição (opcional - deixe vazio para criar novo)</label>
              <input
                type="text"
                name="codRequisicao"
                value={formData.codRequisicao}
                onChange={handleChange}
                placeholder="Digite o código para buscar dados existentes"
              />
              {loadingRequisicao && <small className="text-info">Buscando...</small>}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>ID Laboratório *</label>
                <input
                  type="number"
                  name="idLaboratorio"
                  value={formData.idLaboratorio}
                  onChange={handleChange}
                  required
                />
              </div>

              <div className="form-group">
                <label>ID Unidade *</label>
                <input
                  type="number"
                  name="idUnidade"
                  value={formData.idUnidade}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>ID Paciente *</label>
              <input
                type="number"
                name="idPaciente"
                value={formData.idPaciente}
                onChange={handleChange}
                placeholder="Ex: 87388"
                required
                readOnly={!!requisicaoData}
              />
            </div>

            <div className="form-group">
              <label>Data de Coleta *</label>
              <input
                type="date"
                name="dtaColeta"
                value={formData.dtaColeta}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Convênio e Pagamento</h3>

            <div className="form-group">
              <label>ID Convênio *</label>
              <input
                type="number"
                name="idConvenio"
                value={formData.idConvenio}
                onChange={handleChange}
                placeholder="Ex: 1095"
                required
                readOnly={!!requisicaoData}
              />
            </div>

            <div className="form-group">
              <label>ID Fonte Pagadora *</label>
              <input
                type="number"
                name="idFontePagadora"
                value={formData.idFontePagadora}
                onChange={handleChange}
                placeholder="Ex: 1001"
                required
                readOnly={!!requisicaoData}
              />
            </div>

            <div className="form-group">
              <label>Número da Guia</label>
              <input
                type="text"
                name="numGuia"
                value={formData.numGuia}
                onChange={handleChange}
                placeholder="Ex: 123456789"
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Médico e Local</h3>

            <div className="form-group">
              <label>ID Médico *</label>
              <input
                type="number"
                name="idMedico"
                value={formData.idMedico}
                onChange={handleChange}
                placeholder="Ex: 1"
                required
                readOnly={!!requisicaoData}
              />
            </div>

            <div className="form-group">
              <label>ID Local Origem *</label>
              <input
                type="number"
                name="idLocalOrigem"
                value={formData.idLocalOrigem}
                onChange={handleChange}
                required
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Exames</h3>

            {resultadoConsolidadoFinal?.requisicoes?.[0]?.requisicao?.itens_exame &&
             Array.isArray(resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame) &&
             resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame.length > 0 && (
              <div className="form-group" style={{background: '#f0f9ff', padding: '12px', borderRadius: '6px', marginBottom: '16px'}}>
                <label style={{color: '#0369a1', fontWeight: '600', marginBottom: '8px'}}>
                  📋 Exames Extraídos pelo OCR
                </label>
                <div style={{background: 'white', padding: '10px', borderRadius: '4px', border: '2px solid #bae6fd'}}>
                  {resultadoConsolidadoFinal.requisicoes[0].requisicao.itens_exame.map((exame, idx) => (
                    <div key={idx} style={{
                      padding: '6px 10px',
                      margin: '4px 0',
                      background: '#e0f2fe',
                      borderRadius: '4px',
                      fontSize: '13px',
                      color: '#075985'
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
                      const response = await fetch(`${API_BASE_URL}/api/exames/buscar-por-nome`, {
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

            <div className="form-group">
              <label>ID Exame Principal *</label>
              <input
                type="number"
                name="idExame"
                value={formData.idExame}
                onChange={handleChange}
                placeholder="Ex: 49"
                required
              />
            </div>

            <div className="form-group">
              <label>Exames Convênio * (IDs separados por vírgula)</label>
              <input
                type="text"
                name="examesConvenio"
                value={formData.examesConvenio}
                onChange={handleChange}
                placeholder="CREATININA, FERRITINA, FERRO SÉRICO..."
                required
              />
              <small>Digite os nomes dos exames separados por vírgula</small>
            </div>
          </div>

          {/* Painel JSON Consolidado Final */}
          {resultadoConsolidadoFinal && (
            <div className="form-section">
              <div className="json-consolidado-header">
                <h3>Resultados Consolidados - Formato Completo</h3>
                <button
                  type="button"
                  className="btn-copy-json"
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(resultadoConsolidadoFinal, null, 2));
                    setMessage({ type: 'success', text: 'JSON consolidado copiado!' });
                  }}
                >
                  Copiar JSON Consolidado
                </button>
                <button
                  type="button"
                  className="btn-download-json"
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(resultadoConsolidadoFinal, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `resultados_consolidados_${formData.codRequisicao}_${new Date().toISOString().replace(/:/g, '-')}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Download JSON
                </button>
              </div>
              <div className="json-viewer">
                <pre>{JSON.stringify(resultadoConsolidadoFinal, null, 2)}</pre>
              </div>
            </div>
          )}

          {/* Exibir Imagens se existirem */}
          {imagens.length > 0 && (
            <div className="form-section">
              <h3>Imagens da Requisição ({imagens.length})</h3>
              {loadingOCR && (
                <div className="ocr-status">
                  <span className="loading-spinner"></span>
                  Processando OCR automaticamente...
                </div>
              )}
              <div className="images-grid">
                {imagens.map((img, index) => {
                  const isPDF = img.nome.toUpperCase().endsWith('.PDF');
                  return (
                  <div key={img.id} className={`image-item ${imagensProcessadas.has(img.nome) ? 'processada' : ''}`}>
                    {imagensProcessadas.has(img.nome) && (
                      <div className="badge-processada">✓ OCR Processado</div>
                    )}
                    {isPDF ? (
                      <div className="pdf-preview" onClick={() => abrirImagem(img)}>
                        <div className="pdf-icon">📄</div>
                        <div className="pdf-label">PDF</div>
                      </div>
                    ) : (
                      <img
                        src={img.url}
                        alt={`Imagem ${index + 1}`}
                        onClick={() => abrirImagem(img)}
                        onError={(e) => {
                          console.error('Erro ao carregar imagem:', img.nome, img.url);
                          e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EErro ao carregar%3C/text%3E%3C/svg%3E';
                        }}
                        onLoad={() => console.log('Imagem carregada:', img.nome)}
                      />
                    )}
                    <div className="image-info">
                      <span className="image-type">Tipo: {img.tipo}</span>
                      <span className="image-name">{img.nome}</span>
                      <button
                        type="button"
                        className="btn-ocr"
                        onClick={(e) => {
                          e.stopPropagation();
                          processarOCR(img.url, img.nome, false);
                        }}
                        disabled={loadingOCR || imagensProcessadas.has(img.nome)}
                      >
                        {imagensProcessadas.has(img.nome) ? '✓ Processado' : loadingOCR ? 'Processando...' : 'Processar OCR'}
                      </button>
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}

          {message && (
            <div className={`message message-${message.type}`}>
              {message.text}
            </div>
          )}

          <div className="form-actions">
            <button
              type="button"
              onClick={handleValidate}
              className="btn btn-secondary"
              disabled={loading || loadingRequisicao}
            >
              {loading ? 'Validando...' : 'Validar Dados'}
            </button>

            <button
              type="button"
              onClick={consolidarResultados}
              className="btn btn-secondary"
              disabled={!requisicaoData}
              style={{ background: 'linear-gradient(135deg, #28a745 0%, #20c997 100%)' }}
            >
              Gerar JSON Consolidado
            </button>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || loadingRequisicao}
            >
              {loading ? 'Salvando...' : 'Salvar Admissão'}
            </button>
          </div>
        </form>
      </div>

      {/* Modal para visualizar imagem ou PDF */}
      {imagemSelecionada && (
        <div className="image-modal" onClick={fecharModal}>
          <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={fecharModal}>&times;</button>

            {/* Controles de Zoom e Processar OCR */}
            <div className="modal-header-controls">
              {/* Controles de Zoom */}
              {!imagemSelecionada.nome.toUpperCase().endsWith('.PDF') && (
                <div className="zoom-controls">
                  <button onClick={zoomOut} title="Diminuir zoom">-</button>
                  <button onClick={resetZoom} title="Resetar zoom">{Math.round(zoomLevel * 100)}%</button>
                  <button onClick={zoomIn} title="Aumentar zoom">+</button>
                </div>
              )}

              {/* Botão Processar OCR */}
              <button
                className="btn-processar-ocr"
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
                  className="pdf-viewer"
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

            <div className="modal-footer">
              <p>{imagemSelecionada.nome}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdmissionView;
