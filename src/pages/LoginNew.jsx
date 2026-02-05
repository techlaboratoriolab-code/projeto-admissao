import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { DEPARTMENTS } from '../utils/permissions';

const Login = () => {
  const navigate = useNavigate();
  const { signIn, signUp, resetPassword } = useAuth();
  
  const [isSignUp, setIsSignUp] = useState(false);
  const [isForgotPassword, setIsForgotPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Formulário de Login
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Formulário de Registro
  const [name, setName] = useState('');
  const [username, setUsername] = useState('');
  const [department, setDepartment] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isSignUp) {
        // Registro
        console.log('🔍 Dados do registro:', {
          email,
          password: '***',
          name,
          department,
          username
        });
        
        const { error } = await signUp(email, password, name, department, username);
        
        console.log('📝 Resposta do signUp:', { error });
        
        if (error) {
          console.error('❌ Erro no registro:', error);
          let userFriendlyMessage = error.message;
          
          if (error.message.includes('User already registered')) {
            userFriendlyMessage = 'Este email já está cadastrado. Tente fazer login ou use outro email.';
          } else if (error.message.includes('Password should be at least')) {
            userFriendlyMessage = 'A senha deve ter pelo menos 6 caracteres.';
          } else if (error.message.includes('Invalid email')) {
            userFriendlyMessage = 'Por favor, insira um endereço de email válido.';
          }
          
          setError(userFriendlyMessage);
        } else {
          // Sucesso no registro - fazer login automático
          console.log('✅ Registro bem-sucedido! Fazendo login...');
          
          const { error: loginError } = await signIn(email, password);
          
          if (loginError) {
            console.log('⚠️ Login automático falhou, mas conta foi criada. Redirecionando para login manual...');
            setIsSignUp(false);
            setPassword('');
            alert('✅ Conta criada com sucesso! Agora faça login com suas credenciais.');
          } else {
            console.log('✅ Login automático bem-sucedido!');
            navigate('/admissao');
          }
        }
      } else {
        // Login - aceita email ou username
        let loginEmail = email;
        
        // Se não for email, converte username para email @lab.local
        if (!email.includes('@')) {
          loginEmail = `${email}@lab.local`;
        }
        
        const { error } = await signIn(loginEmail, password);

        if (error) {
          let userFriendlyMessage = error.message;
          
          if (error.message.includes('Invalid login credentials')) {
            userFriendlyMessage = 'Email ou senha incorretos. Verifique suas credenciais e tente novamente.';
          } else if (error.message.includes('Email not confirmed')) {
            userFriendlyMessage = 'Por favor, confirme seu email antes de fazer login.';
          }
          
          setError(userFriendlyMessage);
        } else {
          // Sucesso no login
          navigate('/admissao');
        }
      }
    } catch (err) {
      setError('Ocorreu um erro inesperado. Tente novamente.');
      console.error('Erro:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const { error } = await resetPassword(email);
      
      if (error) {
        setError('Erro ao enviar email de recuperação.');
      } else {
        alert('✅ Instruções de redefinição enviadas para seu email.');
        setIsForgotPassword(false);
        setEmail('');
      }
    } catch (err) {
      setError('Ocorreu um erro inesperado. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-neutral-950 dark:via-blue-950 dark:to-indigo-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated gradient mesh background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Animated orbs */}
        <div className="absolute top-1/4 -left-20 w-96 h-96 bg-gradient-to-r from-blue-200/50 to-cyan-200/50 dark:from-blue-900/30 dark:to-cyan-900/30 rounded-full blur-3xl animate-blob"></div>
        <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-gradient-to-r from-indigo-200/50 to-blue-200/50 dark:from-indigo-900/30 dark:to-blue-900/30 rounded-full blur-3xl animate-blob animation-delay-2000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-r from-slate-200/30 to-blue-200/30 dark:from-slate-900/20 dark:to-blue-900/20 rounded-full blur-3xl animate-pulse-soft"></div>
        
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(30,58,138,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(30,58,138,0.03)_1px,transparent_1px)] dark:bg-[linear-gradient(rgba(148,163,184,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,0.05)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
      </div>

      <div className="max-w-md w-full bg-white/80 dark:bg-neutral-900/80 backdrop-blur-2xl rounded-3xl shadow-2xl shadow-slate-900/10 dark:shadow-neutral-950/50 p-8 animate-scale-in relative z-10 border border-slate-200/50 dark:border-neutral-700/50">
        {/* Subtle glow effect behind card */}
        <div className="absolute -inset-1 bg-gradient-to-r from-blue-500/10 via-indigo-500/10 to-slate-500/10 dark:from-blue-500/5 dark:via-indigo-500/5 dark:to-slate-500/5 rounded-3xl blur-xl -z-10"></div>
        
        <div className="text-center mb-8">
          {/* Modern logo container with rotating border */}
          <div className="relative inline-flex items-center justify-center mb-6">
            {/* Outer rotating ring */}
            <div className="absolute w-28 h-28 rounded-full border-2 border-transparent animate-spin-slow" style={{ background: 'linear-gradient(white, white) padding-box, linear-gradient(to right, #1e3a8a, #3b82f6, #1e40af) border-box', animationDuration: '8s' }}></div>
            
            {/* Logo background with glassmorphism */}
            <div className="relative w-24 h-24 rounded-full bg-gradient-primary flex items-center justify-center shadow-lg shadow-blue-900/10 border border-blue-200/50">
              <span className="text-white text-3xl font-bold">LAB</span>
            </div>
          </div>
          
          <h1 className="text-3xl font-bold mb-1">
            <span className="bg-gradient-to-r from-blue-900 via-blue-700 to-indigo-800 dark:from-blue-400 dark:via-blue-300 dark:to-indigo-400 bg-clip-text text-transparent">
              Sistema de Admissão
            </span>
          </h1>
          <p className="text-slate-500 dark:text-neutral-400 text-sm transition-all duration-300">
            {isForgotPassword 
              ? 'Recuperar senha' 
              : isSignUp 
                ? 'Criar nova conta' 
                : 'Faça login para continuar'
            }
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900/50 rounded-xl text-red-700 dark:text-red-300 text-sm animate-shake flex items-center gap-2">
            <span className="flex-shrink-0 w-5 h-5 bg-red-100 dark:bg-red-900/50 rounded-full flex items-center justify-center text-red-500 dark:text-red-400 font-bold text-xs">!</span>
            {error}
          </div>
        )}  

        {!isForgotPassword ? (
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email ou Username */}
            <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
              <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
                {isSignUp ? 'Email' : 'Email ou Usuário'}
              </label>
              <input
                type={isSignUp ? 'email' : 'text'}
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
                placeholder={isSignUp ? 'seu@email.com' : 'email ou username'}
              />
            </div>

            {/* Campos de Registro */}
            {isSignUp && (
              <>
                <div className="animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
                  <label htmlFor="username" className="block text-sm font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
                    Nome de Usuário *
                  </label>
                  <input
                    type="text"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
                    placeholder="usuario123"
                  />
                </div>

                <div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
                  <label htmlFor="name" className="block text-sm font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
                    Nome Completo *
                  </label>
                  <input
                    type="text"
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
                    placeholder="Seu nome completo"
                  />
                </div>

                <div className="animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
                  <label htmlFor="department" className="block text-sm font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
                    Departamento *
                  </label>
                  <select
                    id="department"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    required
                    className="w-full px-4 py-3 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 cursor-pointer"
                  >
                    <option value="" className="text-slate-400 dark:text-neutral-500">Selecione um departamento</option>
                    {DEPARTMENTS.map((dept) => (
                      <option key={dept} value={dept}>
                        {dept}
                      </option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {/* Senha */}
            <div className="animate-fade-in-up" style={{ animationDelay: isSignUp ? '0.35s' : '0.2s' }}>
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-neutral-300 mb-1.5">
                Senha {isSignUp && '(mínimo 6 caracteres)'}
              </label>
              <div className="relative group">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 pr-11 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
                  placeholder="••••••••"
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 dark:text-neutral-500 hover:text-slate-600 dark:hover:text-neutral-300 transition-colors p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-neutral-700"
                >
                  {showPassword ? (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            
            {/* Botão Submit */}
            <button
              type="submit"
              disabled={loading}
              className="relative w-full py-3.5 px-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center font-semibold overflow-hidden group animate-fade-in-up shadow-lg shadow-blue-900/20 dark:shadow-blue-950/40 hover:shadow-xl hover:shadow-blue-900/30 dark:hover:shadow-blue-950/60"
              style={{ animationDelay: isSignUp ? '0.35s' : '0.3s' }}
            >
              {/* Button gradient background */}
              <div className="absolute inset-0 bg-gradient-to-r from-blue-900 via-blue-700 to-indigo-800 transition-all duration-300 group-hover:scale-105"></div>
              
              {/* Shimmer effect on hover */}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,0.15)_50%,transparent_75%)] bg-[length:250%_250%] animate-shimmer"></div>
              
              {/* Button content */}
              <span className="relative z-10 flex items-center text-white">
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    {isSignUp ? 'Criando conta...' : 'Entrando...'}
                  </>
                ) : (
                  <>
                    {isSignUp ? (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                        </svg>
                        Criar Conta
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                        </svg>
                        Entrar
                      </>
                    )}
                  </>
                )}
              </span>
            </button>
          </form>
        ) : (
          // Formulário de Recuperação de Senha
          <form onSubmit={handleForgotPassword} className="space-y-5 animate-fade-in-up">
            <p className="text-sm text-slate-600 dark:text-neutral-400">Digite seu email para redefinir a senha.</p>
            
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.com"
              required
              className="w-full px-4 py-3 border border-slate-200 dark:border-neutral-700 rounded-xl focus:ring-2 focus:ring-blue-500/30 dark:focus:ring-blue-400/30 focus:border-blue-500 dark:focus:border-blue-400 transition-all duration-200 hover:border-slate-300 dark:hover:border-neutral-600 bg-white/70 dark:bg-neutral-800/70 backdrop-blur-sm text-slate-800 dark:text-neutral-100 placeholder:text-slate-400 dark:placeholder:text-neutral-500"
            />
            
            <button
              type="submit"
              disabled={loading}
              className="relative w-full py-3.5 px-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 flex items-center justify-center font-semibold overflow-hidden group shadow-lg shadow-blue-900/20 dark:shadow-blue-950/40"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-900 via-blue-700 to-indigo-800 transition-all duration-300 group-hover:scale-105"></div>
              <span className="relative z-10 text-white">
                {loading ? 'Enviando...' : 'Enviar instruções'}
              </span>
            </button>
          </form>
        )}

        {/* Links de navegação */}
        <div className="mt-6 text-center space-y-3">
          <button
            onClick={() => {
              setIsSignUp(!isSignUp);
              setIsForgotPassword(false);
              setName('');
              setUsername('');
              setDepartment('');
              setError(null);
            }}
            className="text-blue-700 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300 text-sm font-medium transition-colors hover:underline underline-offset-4 block w-full"
          >
            {isSignUp 
              ? 'Já tem uma conta? Faça login' 
              : 'Não tem uma conta? Cadastre-se'
            }
          </button>
          
          {!isSignUp && (
            <button
              onClick={() => {
                setIsForgotPassword(!isForgotPassword);
                setError(null);
              }}
              className="text-slate-500 dark:text-neutral-400 hover:text-blue-700 dark:hover:text-blue-400 text-sm transition-colors block w-full"
            >
              {isForgotPassword ? 'Voltar ao login' : 'Esqueci minha senha'}
            </button>
          )}
        </div>

        {isSignUp && (
          <div className="mt-5 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 border border-blue-200 dark:border-blue-900/50 rounded-xl text-slate-700 dark:text-neutral-300 text-xs animate-fade-in-up">
            <strong className="text-blue-800 dark:text-blue-400">Nota:</strong> Após criar sua conta, você poderá acessar o sistema de admissão.
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
