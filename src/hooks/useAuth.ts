import { useState, useEffect } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { adminUpdateUser } from '../lib/supabaseAdminApi';
import { UserProfile, UserRole, Department } from '../types';

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Sessão inicial
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        loadUserProfile(session.user.id);
      } else {
        setLoading(false);
      }
    });

    // Listener para mudanças de auth
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) {
        loadUserProfile(session.user.id);
      } else {
        setUserProfile(null);
        setLoading(false);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const loadUserProfile = async (userId: string) => {
    try {
      // Buscar do user_metadata do auth
      const { data: { user } } = await supabase.auth.getUser();
      
      if (user?.user_metadata) {
        const metadata = user.user_metadata;
        setUserProfile({
          id: user.id,
          email: user.email || '',
          name: metadata.nome || metadata.name || metadata.username || user.email?.split('@')[0] || '',
          role: (metadata.role as UserRole) || 'usuario',
          department: metadata.department as Department,
          username: metadata.username,
          createdAt: user.created_at,
          updatedAt: user.updated_at || user.created_at,
        });
      } else {
        setUserProfile(null);
      }
    } catch (error) {
      console.error('Erro ao carregar perfil:', error);
    } finally {
      setLoading(false);
    }
  };

  const signUp = async (
    email: string,
    password: string,
    name?: string,
    department?: string,
    username?: string
  ) => {
    console.log('🚀 useAuth.signUp chamado com:', {
      email,
      password: '***',
      name,
      department,
      username
    });

    try {
      // Criar usuário no Supabase Auth
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            username: username || email.split('@')[0],
            nome: name || email.split('@')[0],
            department: department || 'Operações',
            role: 'usuario',
          },
        },
      });

      console.log('📬 Resposta do Supabase Auth:', { data, error });

      if (error) {
        console.error('❌ Erro ao criar usuário:', error);
        return { data, error };
      }

      if (data.user) {
        console.log('✅ Usuário criado no Auth, carregando perfil...');
        await loadUserProfile(data.user.id);
      }

      return { data, error };
    } catch (err) {
      console.error('💥 Exceção no signUp:', err);
      return { data: null, error: err };
    }
  };

  const resetPassword = async (email: string) => {
    return await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
  };

  const signIn = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { data, error };
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    setUserProfile(null);
    return { error };
  };

  const updateUserRole = async (userId: string, newRole: UserRole) => {
    try {
      // Usar adminUpdateUser (REST direto) pois supabase.auth.admin.* é bloqueado no browser
      const userData = await adminUpdateUser(userId, {
        user_metadata: { role: newRole }
      });

      if (!userData) throw new Error('Falha ao atualizar role');

      if (userId === user?.id) {
        await loadUserProfile(userId);
      }

      return { success: true };
    } catch (error) {
      console.error('Erro ao atualizar role do usuário:', error);
      return { success: false, error };
    }
  };

  return {
    user,
    session,
    userProfile,
    loading,
    signUp,
    signIn,
    signOut,
    resetPassword,
    updateUserRole,
    refreshProfile: () => user && loadUserProfile(user.id),
    authenticated: !!session,
  };
};
