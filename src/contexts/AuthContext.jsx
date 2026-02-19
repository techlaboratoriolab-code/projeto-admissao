import React, { createContext, useState, useContext, useEffect } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [usuario, setUsuario] = useState(null);
  const [sessao, setSessao] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);

  // Verificar sessão do Supabase ao carregar a aplicação
  useEffect(() => {
    const verificarSessao = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        
        if (session) {
          setSessao(session);
          setUsuario({
            id: session.user.id,
            email: session.user.email,
            username: session.user.user_metadata?.username || session.user.email.split('@')[0],
            role: session.user.user_metadata?.role || 'usuario',
            nome_completo: session.user.user_metadata?.nome_completo || '',
            aplis_usuario: session.user.user_metadata?.aplis_usuario || null,
            aplis_senha: session.user.user_metadata?.aplis_senha || null
          });
        }
      } catch (error) {
        console.error('Erro ao verificar sessão:', error);
        setSessao(null);
        setUsuario(null);
      } finally {
        setCarregando(false);
      }
    };

    verificarSessao();

    // Listener para mudanças de autenticação
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSessao(session);
      if (session) {
        setUsuario({
          id: session.user.id,
          email: session.user.email,
          username: session.user.user_metadata?.username || session.user.email.split('@')[0],
          role: session.user.user_metadata?.role || 'usuario',
          nome_completo: session.user.user_metadata?.nome_completo || '',
          aplis_usuario: session.user.user_metadata?.aplis_usuario || null,
          aplis_senha: session.user.user_metadata?.aplis_senha || null
        });
      } else {
        setUsuario(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // Função de login
  const login = async (emailOrUsername, password) => {
    try {
      setErro(null);

      // Verificar se é email ou username
      const isEmail = emailOrUsername.includes('@');
      let email = emailOrUsername;

      // Se não for email, buscar no user_metadata
      if (!isEmail) {
        // Tentar fazer login direto (Supabase não suporta username direto, então tentamos como email)
        email = `${emailOrUsername}@lab.local`; // Convencionar domínio interno
      }

      const { data, error } = await supabase.auth.signInWithPassword({
        email: email,
        password: password
      });

      if (error) {
        const mensagemErro = error.message === 'Invalid login credentials' 
          ? 'Usuário ou senha inválidos' 
          : error.message;
        setErro(mensagemErro);
        return { sucesso: false, erro: mensagemErro };
      }

      if (data.session) {
        setSessao(data.session);
        setUsuario({
          id: data.user.id,
          email: data.user.email,
          username: data.user.user_metadata?.username || data.user.email.split('@')[0],
          role: data.user.user_metadata?.role || 'usuario',
          nome_completo: data.user.user_metadata?.nome_completo || '',
          aplis_usuario: data.user.user_metadata?.aplis_usuario || null,
          aplis_senha: data.user.user_metadata?.aplis_senha || null
        });
        return { sucesso: true };
      }

      return { sucesso: false, erro: 'Erro ao fazer login' };
    } catch (error) {
      console.error('Erro ao fazer login:', error);
      const mensagemErro = 'Erro ao conectar com o servidor';
      setErro(mensagemErro);
      return { sucesso: false, erro: mensagemErro };
    }
  };

  // Função de registro
  const registrar = async (dadosRegistro) => {
    try {
      setErro(null);

      console.log('🔍 Tentando registrar usuário:', {
        email: dadosRegistro.email,
        username: dadosRegistro.username
      });

      const { data, error } = await supabase.auth.signUp({
        email: dadosRegistro.email,
        password: dadosRegistro.senha,
        options: {
          data: {
            username: dadosRegistro.username,
            nome_completo: dadosRegistro.nome_completo || '',
            telefone: dadosRegistro.telefone || '',
            role: 'usuario' // Primeiro usuário pode ser admin manualmente depois
          }
        }
      });

      if (error) {
        console.error('❌ Erro do Supabase:', error);
        const mensagemErro = error.message === 'User already registered'
          ? 'Este email já está cadastrado'
          : error.message;
        setErro(mensagemErro);
        return { sucesso: false, erro: mensagemErro };
      }

      console.log('✅ Resposta do Supabase:', data);

      if (data.user) {
        console.log('✅ Usuário criado com sucesso!', data.user);
        return { sucesso: true, mensagem: 'Cadastro realizado com sucesso! Faça login.' };
      }

      return { sucesso: false, erro: 'Erro ao criar usuário' };
    } catch (error) {
      console.error('❌ Erro ao registrar:', error);
      const mensagemErro = 'Erro ao conectar com o servidor';
      setErro(mensagemErro);
      return { sucesso: false, erro: mensagemErro };
    }
  };

  // Função de logout
  const logout = async () => {
    try {
      await supabase.auth.signOut();
      setSessao(null);
      setUsuario(null);
    } catch (error) {
      console.error('Erro ao fazer logout:', error);
    }
  };

  // Função para atualizar perfil do usuário
  const atualizarPerfil = async (dadosAtualizados) => {
    setErro(null);

    try {
      const { data, error } = await supabase.auth.updateUser({
        data: dadosAtualizados
      });

      if (error) {
        setErro(error.message);
        return { sucesso: false, erro: error.message };
      }

      if (data.user) {
        setUsuario({
          id: data.user.id,
          email: data.user.email,
          username: data.user.user_metadata?.username || data.user.email.split('@')[0],
          role: data.user.user_metadata?.role || 'usuario',
          nome_completo: data.user.user_metadata?.nome_completo || '',
          aplis_usuario: data.user.user_metadata?.aplis_usuario || null,
          aplis_senha: data.user.user_metadata?.aplis_senha || null
        });
        return { sucesso: true };
      }

      return { sucesso: false, erro: 'Erro ao atualizar perfil' };
    } catch (error) {
      console.error('Erro ao atualizar perfil:', error);
      const mensagemErro = 'Erro ao conectar com o servidor';
      setErro(mensagemErro);
      return { sucesso: false, erro: mensagemErro };
    }
  };

  // Função auxiliar para verificar se usuário é admin
  const isAdmin = () => {
    return usuario?.role === 'admin';
  };

  // Função auxiliar para verificar se usuário é supervisor
  const isSupervisor = () => {
    return usuario?.role === 'supervisor' || usuario?.role === 'admin';
  };

  // Função para obter headers de autorização
  const getAuthHeaders = () => {
    if (sessao?.access_token) {
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessao.access_token}`
      };
    }
    return {
      'Content-Type': 'application/json'
    };
  };

  const value = {
    usuario,
    sessao,
    carregando,
    erro,
    login,
    registrar,
    logout,
    atualizarPerfil,
    isAdmin,
    isSupervisor,
    getAuthHeaders,
    estaAutenticado: !!sessao && !!usuario
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

// Hook customizado para usar o contexto de autenticação
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de um AuthProvider');
  }
  return context;
};

export default AuthContext;
