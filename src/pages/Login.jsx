import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import config from '../config';

const API_BASE_URL = config.API_BASE_URL;

const Login = () => {
  const [username, setUsername] = useState('');
  const [senha, setSenha] = useState('');
  const [erroLocal, setErroLocal] = useState('');
  const [carregandoLogin, setCarregandoLogin] = useState(false);

  // Estados para modal de registro
  const [mostrarModalRegistro, setMostrarModalRegistro] = useState(false);
  const [registroData, setRegistroData] = useState({
    username: '',
    email: '',
    senha: '',
    confirmarSenha: '',
    nome_completo: '',
    telefone: ''
  });
  const [erroRegistro, setErroRegistro] = useState('');
  const [sucessoRegistro, setSucessoRegistro] = useState(false);
  const [carregandoRegistro, setCarregandoRegistro] = useState(false);

  const { login, registrar, estaAutenticado, erro } = useAuth();
  const navigate = useNavigate();

  // Redirecionar se já estiver autenticado
  useEffect(() => {
    if (estaAutenticado) {
      navigate('/admissao');
    }
  }, [estaAutenticado, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErroLocal('');

    // Validação básica
    if (!username.trim()) {
      setErroLocal('Por favor, informe o nome de usuário');
      return;
    }

    if (!senha) {
      setErroLocal('Por favor, informe a senha');
      return;
    }

    setCarregandoLogin(true);

    try {
      const resultado = await login(username.trim(), senha);

      if (resultado.sucesso) {
        // Redirecionar para página de admissão
        navigate('/admissao');
      } else {
        setErroLocal(resultado.erro || 'Erro ao fazer login');
      }
    } catch (error) {
      setErroLocal('Erro ao conectar com o servidor');
    } finally {
      setCarregandoLogin(false);
    }
  };

  const handleRegistro = async (e) => {
    e.preventDefault();
    setErroRegistro('');

    // Validações
    if (!registroData.username.trim()) {
      setErroRegistro('Nome de usuário é obrigatório');
      return;
    }

    if (!registroData.email.trim()) {
      setErroRegistro('Email é obrigatório');
      return;
    }

    if (!registroData.senha) {
      setErroRegistro('Senha é obrigatória');
      return;
    }

    if (registroData.senha.length < 6) {
      setErroRegistro('A senha deve ter no mínimo 6 caracteres');
      return;
    }

    if (registroData.senha !== registroData.confirmarSenha) {
      setErroRegistro('As senhas não coincidem');
      return;
    }

    if (!registroData.nome_completo.trim()) {
      setErroRegistro('Nome completo é obrigatório');
      return;
    }

    setCarregandoRegistro(true);

    try {
      const resultado = await registrar({
        username: registroData.username.trim(),
        email: registroData.email.trim(),
        senha: registroData.senha,
        nome_completo: registroData.nome_completo.trim(),
        telefone: registroData.telefone.trim()
      });

      if (resultado.sucesso) {
        setSucessoRegistro(true);
        setErroRegistro('');

        // Após 2 segundos, fechar modal e usuário pode fazer login
        setTimeout(() => {
          setUsername(registroData.email); // Usar email para login
          setMostrarModalRegistro(false);
          setSucessoRegistro(false);
          setRegistroData({
            username: '',
            email: '',
            senha: '',
            confirmarSenha: '',
            nome_completo: '',
            telefone: ''
          });
        }, 2000);
      } else {
        setErroRegistro(resultado.erro || 'Erro ao criar conta');
      }
    } catch (error) {
      setErroRegistro('Erro ao conectar com o servidor');
    } finally {
      setCarregandoRegistro(false);
    }
  };

  const abrirModalRegistro = () => {
    setMostrarModalRegistro(true);
    setErroRegistro('');
    setSucessoRegistro(false);
  };

  const fecharModalRegistro = () => {
    setMostrarModalRegistro(false);
    setRegistroData({
      username: '',
      email: '',
      senha: '',
      confirmarSenha: '',
      nome_completo: '',
      telefone: ''
    });
    setErroRegistro('');
    setSucessoRegistro(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-primary p-5">
      <div className="bg-white rounded-2xl shadow-modal p-10 w-full max-w-[420px] animate-slideUp max-[480px]:p-6">
        {/* Logo LAB */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-primary text-white text-[28px] font-bold rounded-full mb-4 shadow-primary max-[480px]:w-16 max-[480px]:h-16 max-[480px]:text-2xl">
            LAB
          </div>
          <h1 className="text-2xl font-semibold text-neutral-700 m-0 max-[480px]:text-xl">
            Sistema de Admissão
          </h1>
        </div>

        {/* Formulário de Login */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <label htmlFor="username" className="text-sm font-medium text-neutral-600">
              Usuário
            </label>
            <input
              id="username"
              type="text"
              className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Digite seu usuário"
              autoComplete="username"
              disabled={carregandoLogin}
              autoFocus
            />
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="senha" className="text-sm font-medium text-neutral-600">
              Senha
            </label>
            <input
              id="senha"
              type="password"
              className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="Digite sua senha"
              autoComplete="current-password"
              disabled={carregandoLogin}
            />
          </div>

          {/* Mensagem de erro */}
          {(erroLocal || erro) && (
            <div className="px-4 py-3 bg-error-light border border-red-400 rounded-lg text-error-dark text-sm animate-shake">
              {erroLocal || erro}
            </div>
          )}

          {/* Botão de login */}
          <button
            type="submit"
            className="px-6 py-3.5 bg-gradient-primary text-white border-0 rounded-lg text-base font-semibold cursor-pointer transition-all mt-2 hover:not-disabled:translate-y-[-2px] hover:not-disabled:shadow-primary active:not-disabled:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed"
            disabled={carregandoLogin}
          >
            {carregandoLogin ? 'Entrando...' : 'Entrar'}
          </button>

          {/* Botão de Primeiro Acesso */}
          <button
            type="button"
            className="px-6 py-3 bg-white text-primary border-2 border-primary rounded-lg text-[15px] font-semibold cursor-pointer transition-all hover:not-disabled:bg-neutral-50 hover:not-disabled:translate-y-[-1px] disabled:opacity-60 disabled:cursor-not-allowed"
            onClick={abrirModalRegistro}
            disabled={carregandoLogin}
          >
            Primeiro Acesso
          </button>
        </form>

        {/* Modal de Registro */}
        {mostrarModalRegistro && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center p-5 z-[1000] animate-fadeIn" onClick={fecharModalRegistro}>
            <div className="bg-white rounded-2xl w-full max-w-[500px] max-h-[90vh] overflow-y-auto shadow-modal animate-slideUp" onClick={(e) => e.stopPropagation()}>
              <div className="flex justify-between items-center px-6 pt-6 pb-4 border-b border-neutral-200">
                <h2 className="m-0 text-[22px] font-semibold text-neutral-700">Criar Nova Conta</h2>
                <button className="bg-transparent border-0 text-[32px] text-neutral-400 cursor-pointer leading-none p-0 w-8 h-8 flex items-center justify-center rounded transition-all hover:bg-neutral-50 hover:text-neutral-600" onClick={fecharModalRegistro}>
                  ×
                </button>
              </div>

              {sucessoRegistro ? (
                <div className="px-6 py-8 text-center">
                  <div className="px-5 py-4 bg-success-light border border-green-400 rounded-lg text-green-900 text-base">
                    ✅ Conta criada com sucesso! Redirecionando...
                  </div>
                </div>
              ) : (
                <form onSubmit={handleRegistro} className="p-6">
                  <div className="flex flex-col gap-5">
                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-username" className="text-sm font-medium text-neutral-600">
                        Nome de Usuário *
                      </label>
                      <input
                        id="reg-username"
                        type="text"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.username}
                        onChange={(e) => setRegistroData({...registroData, username: e.target.value})}
                        placeholder="Digite seu nome de usuário"
                        disabled={carregandoRegistro}
                        autoFocus
                      />
                    </div>

                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-nome" className="text-sm font-medium text-neutral-600">
                        Nome Completo *
                      </label>
                      <input
                        id="reg-nome"
                        type="text"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.nome_completo}
                        onChange={(e) => setRegistroData({...registroData, nome_completo: e.target.value})}
                        placeholder="Digite seu nome completo"
                        disabled={carregandoRegistro}
                      />
                    </div>

                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-email" className="text-sm font-medium text-neutral-600">
                        Email *
                      </label>
                      <input
                        id="reg-email"
                        type="email"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.email}
                        onChange={(e) => setRegistroData({...registroData, email: e.target.value})}
                        placeholder="Digite seu email"
                        disabled={carregandoRegistro}
                      />
                    </div>

                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-telefone" className="text-sm font-medium text-neutral-600">
                        Telefone (opcional)
                      </label>
                      <input
                        id="reg-telefone"
                        type="tel"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.telefone}
                        onChange={(e) => setRegistroData({...registroData, telefone: e.target.value})}
                        placeholder="(XX) XXXXX-XXXX"
                        disabled={carregandoRegistro}
                      />
                    </div>

                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-senha" className="text-sm font-medium text-neutral-600">
                        Senha * (mínimo 6 caracteres)
                      </label>
                      <input
                        id="reg-senha"
                        type="password"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.senha}
                        onChange={(e) => setRegistroData({...registroData, senha: e.target.value})}
                        placeholder="Digite sua senha"
                        disabled={carregandoRegistro}
                      />
                    </div>

                    <div className="flex flex-col gap-2">
                      <label htmlFor="reg-confirmar" className="text-sm font-medium text-neutral-600">
                        Confirmar Senha *
                      </label>
                      <input
                        id="reg-confirmar"
                        type="password"
                        className="px-4 py-3 border-2 border-neutral-200 rounded-lg text-[15px] transition-all outline-none placeholder:text-neutral-400 focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.1)] disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                        value={registroData.confirmarSenha}
                        onChange={(e) => setRegistroData({...registroData, confirmarSenha: e.target.value})}
                        placeholder="Confirme sua senha"
                        disabled={carregandoRegistro}
                      />
                    </div>

                    {erroRegistro && (
                      <div className="px-4 py-3 bg-error-light border border-red-400 rounded-lg text-error-dark text-sm animate-shake">
                        {erroRegistro}
                      </div>
                    )}

                    <div className="flex gap-3 pt-4 border-t border-neutral-200">
                      <button
                        type="button"
                        className="flex-1 px-5 py-3 bg-neutral-100 text-neutral-600 border-2 border-neutral-200 rounded-lg text-[15px] font-semibold cursor-pointer transition-all hover:not-disabled:bg-neutral-200 disabled:opacity-60 disabled:cursor-not-allowed"
                        onClick={fecharModalRegistro}
                        disabled={carregandoRegistro}
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        className="flex-1 px-5 py-3 bg-gradient-primary text-white border-0 rounded-lg text-[15px] font-semibold cursor-pointer transition-all hover:not-disabled:translate-y-[-1px] hover:not-disabled:shadow-primary disabled:opacity-60 disabled:cursor-not-allowed"
                        disabled={carregandoRegistro}
                      >
                        {carregandoRegistro ? 'Criando...' : 'Criar Conta'}
                      </button>
                    </div>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
