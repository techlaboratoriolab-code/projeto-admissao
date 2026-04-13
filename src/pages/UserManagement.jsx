import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import {
  adminListUsers,
  adminCreateUser,
  adminUpdateUser,
  adminBanUser,
  adminUnbanUser,
} from '../lib/supabaseAdminApi';
import { DEPARTMENTS } from '../utils/permissions';

const UserManagement = () => {
  const { user: usuarioLogado, userProfile } = useAuth();

  const [usuarios, setUsuarios] = useState([]);
  const [estatisticas, setEstatisticas] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(null);
  const [sucesso, setSucesso] = useState(null);
  const [filtroRole, setFiltroRole] = useState('todos');
  const [filtroDepartamento, setFiltroDepartamento] = useState('todos');
  const [buscaTexto, setBuscaTexto] = useState('');

  const [modalAberto, setModalAberto] = useState(false);
  const [modoEdicao, setModoEdicao] = useState(false);
  const [usuarioEditando, setUsuarioEditando] = useState(null);

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    senha: '',
    nome: '',
    department: '',
    role: 'usuario',
    aplis_usuario: '',
    aplis_senha: ''
  });

  // Carregar usuários ao montar o componente
  useEffect(() => {
    carregarUsuarios();
  }, []);

  const carregarUsuarios = async () => {
    try {
      setCarregando(true);
      setErro(null);

      // Buscar usuários do Supabase Auth (via REST direto — supabase-js v2 bloqueia admin no browser)
      const users = await adminListUsers();

      // Formatar usuários com novo schema
      const usuariosFormatados = users.map(user => ({
        id: user.id,
        username: user.user_metadata?.username || user.email?.split('@')[0] || 'sem_username',
        email: user.email,
        nome: user.user_metadata?.name || user.user_metadata?.nome || '',
        department: user.user_metadata?.department || '',
        role: user.user_metadata?.role || 'usuario',
        aplis_usuario: user.user_metadata?.aplis_usuario || '',
        aplis_senha: user.user_metadata?.aplis_senha || '',
        ativo: !user.banned_until,
        email_confirmado: !!user.email_confirmed_at,
        created_at: user.created_at,
        ultimo_login: user.last_sign_in_at
      }));

      setUsuarios(usuariosFormatados);
      calcularEstatisticas(usuariosFormatados);
    } catch (error) {
      console.error('Erro ao carregar usuários:', error);
      setErro('Erro ao conectar com o servidor');
    } finally {
      setCarregando(false);
    }
  };

  const calcularEstatisticas = (usuarios) => {
    const stats = {
      total_usuarios: usuarios.length,
      usuarios_ativos: usuarios.filter(u => u.ativo).length,
      usuarios_inativos: usuarios.filter(u => !u.ativo).length,
      total_admins: usuarios.filter(u => u.role === 'admin').length,
      total_supervisores: usuarios.filter(u => u.role === 'supervisor').length,
      total_usuarios_basicos: usuarios.filter(u => u.role === 'usuario').length
    };
    setEstatisticas(stats);
  };

  const abrirModalNovo = () => {
    setModoEdicao(false);
    setUsuarioEditando(null);
    setFormData({
      username: '',
      email: '',
      senha: '',
      nome: '',
      department: '',
      role: 'usuario',
      aplis_usuario: '',
      aplis_senha: ''
    });
    setModalAberto(true);
    setErro(null);
    setSucesso(null);
  };

  const abrirModalEdicao = (usuario) => {
    setModoEdicao(true);
    setUsuarioEditando(usuario);
    setFormData({
      username: usuario.username,
      email: usuario.email,
      senha: '', // Senha fica vazia na edição
      nome: usuario.nome || '',
      department: usuario.department || '',
      role: usuario.role,
      aplis_usuario: usuario.aplis_usuario || '',
      aplis_senha: usuario.aplis_senha || ''
    });
    setModalAberto(true);
    setErro(null);
    setSucesso(null);
  };

  const fecharModal = () => {
    setModalAberto(false);
    setModoEdicao(false);
    setUsuarioEditando(null);
    setFormData({
      username: '',
      email: '',
      senha: '',
      nome: '',
      department: '',
      role: 'usuario',
      aplis_usuario: '',
      aplis_senha: ''
    });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErro(null);
    setSucesso(null);

    // Validações
    if (!formData.username.trim()) {
      setErro('Nome de usuário é obrigatório');
      return;
    }

    if (!formData.email.trim()) {
      setErro('E-mail é obrigatório');
      return;
    }

    if (!modoEdicao && !formData.senha) {
      setErro('Senha é obrigatória ao criar novo usuário');
      return;
    }

    if (formData.senha && formData.senha.length < 6) {
      setErro('Senha deve ter no mínimo 6 caracteres');
      return;
    }

    if (!formData.nome.trim()) {
      setErro('Nome completo é obrigatório');
      return;
    }

    if (!formData.department) {
      setErro('Departamento é obrigatório');
      return;
    }

    try {
      const usernameLimpo = formData.username.trim();
      const emailLimpo = formData.email.trim();
      const nomeLimpo = formData.nome.trim();

      if (modoEdicao) {
        // ATUALIZAR USUÁRIO via Supabase Admin
        const updateData = {
          email: emailLimpo,
          user_metadata: {
            username: usernameLimpo,
            name: nomeLimpo,
            department: formData.department,
            role: formData.role,
            aplis_usuario: formData.aplis_usuario || null,
            aplis_senha: formData.aplis_senha || null
          }
        };

        // Se senha foi fornecida, incluir na atualização
        if (formData.senha && formData.senha.trim()) {
          updateData.password = formData.senha;
        }

        await adminUpdateUser(usuarioEditando.id, updateData);

        setSucesso('✅ Usuário atualizado com sucesso!');
      } else {
        // CRIAR NOVO USUÁRIO via REST Admin (supabase-js v2 bloqueia auth.admin no browser)
        await adminCreateUser({
          email: emailLimpo,
          password: formData.senha,
          user_metadata: {
            username: usernameLimpo,
            name: nomeLimpo,
            department: formData.department,
            role: formData.role,
            aplis_usuario: formData.aplis_usuario || null,
            aplis_senha: formData.aplis_senha || null,
          },
        });

        setSucesso('✅ Usuário criado com sucesso!');
      }

      setTimeout(() => {
        fecharModal();
        carregarUsuarios();
      }, 1500);
    } catch (error) {
      console.error('Erro ao salvar usuário:', error);
      setErro('Erro ao salvar usuário: ' + error.message);
    }
  };

  const desativarUsuario = async (usuario) => {
    if (!window.confirm(`Deseja realmente desativar o usuário ${usuario.username}?`)) {
      return;
    }

    try {
      await adminBanUser(usuario.id);
      setSucesso('Usuário desativado com sucesso!');
      setTimeout(() => setSucesso(null), 3000);
      carregarUsuarios();
    } catch (error) {
      console.error('Erro ao desativar usuário:', error);
      setErro('Erro ao desativar usuário');
      setTimeout(() => setErro(null), 5000);
    }
  };

  const ativarUsuario = async (usuario) => {
    try {
      await adminUnbanUser(usuario.id);
      setSucesso('Usuário reativado com sucesso!');
      setTimeout(() => setSucesso(null), 3000);
      carregarUsuarios();
    } catch (error) {
      console.error('Erro ao reativar usuário:', error);
      setErro('Erro ao reativar usuário');
      setTimeout(() => setErro(null), 5000);
    }
  };

  const getDepartmentLabel = (dept) => {
    const department = DEPARTMENTS.find(d => d.id === dept);
    return department ? department.name : dept || 'Não especificado';
  };

  const getRoleLabel = (role) => {
    switch (role) {
      case 'admin': return 'Administrador';
      case 'supervisor': return 'Supervisor';
      case 'usuario': return 'Usuário';
      default: return role;
    }
  };

  // Filtrar usuários
  const usuariosFiltrados = usuarios.filter(usuario => {
    const matchRole = filtroRole === 'todos' || usuario.role === filtroRole;
    const matchDept = filtroDepartamento === 'todos' || usuario.department === filtroDepartamento;
    const matchBusca = 
      buscaTexto === '' ||
      usuario.nome.toLowerCase().includes(buscaTexto.toLowerCase()) ||
      usuario.email.toLowerCase().includes(buscaTexto.toLowerCase()) ||
      usuario.username.toLowerCase().includes(buscaTexto.toLowerCase());
    
    return matchRole && matchDept && matchBusca;
  });

  // Paleta de cores para avatares baseada no initial
  const avatarColor = (str) => {
    const colors = [
      'bg-blue-500', 'bg-violet-500', 'bg-emerald-500', 'bg-amber-500',
      'bg-rose-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-teal-500',
    ];
    const c = (str || 'U').charCodeAt(0) % colors.length;
    return colors[c];
  };

  const inputCls = "w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition";
  const labelCls = "block text-xs font-semibold text-gray-500 dark:text-neutral-400 uppercase tracking-wide mb-1.5";

  if (carregando) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-neutral-950">
        <div className="flex items-center gap-3 text-gray-500 dark:text-neutral-400">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
          </svg>
          <span className="text-sm font-medium">Carregando usuários...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-neutral-950">
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* ── Header ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/30">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-neutral-50 leading-tight">Gerenciamento de Usuários</h1>
              <p className="text-sm text-gray-500 dark:text-neutral-400 mt-0.5">Gerencie acessos, permissões e departamentos</p>
            </div>
          </div>
          <button
            onClick={abrirModalNovo}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-sm font-semibold rounded-lg shadow-sm shadow-blue-600/25 transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Novo Usuário
          </button>
        </div>

        {/* ── Alertas ── */}
        {erro && (
          <div className="mb-5 flex items-start gap-3 p-4 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-300 rounded-xl text-sm">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            {erro}
          </div>
        )}
        {sucesso && (
          <div className="mb-5 flex items-start gap-3 p-4 bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-900/60 text-green-700 dark:text-green-300 rounded-xl text-sm">
            <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
            </svg>
            {sucesso}
          </div>
        )}

        {/* ── Cards de Estatísticas ── */}
        {estatisticas && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Total de Usuários', value: estatisticas.total_usuarios, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-950/50',
                icon: <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/> },
              { label: 'Usuários Ativos', value: estatisticas.usuarios_ativos, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/50',
                icon: <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/> },
              { label: 'Administradores', value: estatisticas.total_admins, color: 'text-violet-600 dark:text-violet-400', bg: 'bg-violet-50 dark:bg-violet-950/50',
                icon: <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/> },
              { label: 'Supervisores', value: estatisticas.total_supervisores, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/50',
                icon: <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/> },
            ].map((card, i) => (
              <div key={i} className="bg-white dark:bg-neutral-900 rounded-xl border border-gray-100 dark:border-neutral-800 p-5 flex items-center gap-4">
                <div className={`w-10 h-10 rounded-lg ${card.bg} flex items-center justify-center flex-shrink-0`}>
                  <svg className={`w-5 h-5 ${card.color}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                    {card.icon}
                  </svg>
                </div>
                <div>
                  <div className={`text-2xl font-bold ${card.color}`}>{card.value}</div>
                  <div className="text-xs text-gray-500 dark:text-neutral-400 font-medium mt-0.5">{card.label}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── Barra de Filtros ── */}
        <div className="bg-white dark:bg-neutral-900 rounded-xl border border-gray-100 dark:border-neutral-800 px-5 py-4 mb-5 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
            </svg>
            <input
              type="text"
              placeholder="Buscar por nome, e-mail ou usuário..."
              value={buscaTexto}
              onChange={(e) => setBuscaTexto(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition"
            />
          </div>
          <select
            value={filtroRole}
            onChange={(e) => setFiltroRole(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition min-w-[150px]"
          >
            <option value="todos">Todos os perfis</option>
            <option value="admin">Administrador</option>
            <option value="supervisor">Supervisor</option>
            <option value="usuario">Usuário</option>
          </select>
          <select
            value={filtroDepartamento}
            onChange={(e) => setFiltroDepartamento(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition min-w-[180px]"
          >
            <option value="todos">Todos os departamentos</option>
            {DEPARTMENTS.map(dept => (
              <option key={dept.id} value={dept.id}>{dept.name}</option>
            ))}
          </select>
        </div>

        {/* ── Tabela ── */}
        <div className="bg-white dark:bg-neutral-900 rounded-xl border border-gray-100 dark:border-neutral-800 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 dark:border-neutral-800 flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-neutral-400 font-medium">
              {usuariosFiltrados.length} de {usuarios.length} usuário{usuarios.length !== 1 ? 's' : ''}
            </span>
            {(buscaTexto || filtroRole !== 'todos' || filtroDepartamento !== 'todos') && (
              <button
                onClick={() => { setBuscaTexto(''); setFiltroRole('todos'); setFiltroDepartamento('todos'); }}
                className="text-xs text-blue-600 dark:text-blue-400 hover:underline font-medium"
              >
                Limpar filtros
              </button>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100 dark:border-neutral-800">
                  {['Usuário', 'Nome Completo', 'E-mail', 'Departamento', 'Perfil', 'Status', ''].map((h, i) => (
                    <th key={i} className="px-5 py-3 text-left text-xs font-semibold text-gray-400 dark:text-neutral-500 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-neutral-800">
                {usuariosFiltrados.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center py-16">
                      <div className="flex flex-col items-center gap-3 text-gray-400 dark:text-neutral-500">
                        <svg className="w-10 h-10 opacity-40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
                        </svg>
                        <span className="text-sm">
                          {buscaTexto || filtroRole !== 'todos' || filtroDepartamento !== 'todos'
                            ? 'Nenhum usuário encontrado com os filtros aplicados'
                            : 'Nenhum usuário cadastrado'}
                        </span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  usuariosFiltrados.map((usuario) => {
                    const initial = (usuario.nome?.charAt(0) || usuario.username?.charAt(0) || 'U').toUpperCase();
                    return (
                      <tr key={usuario.id} className="hover:bg-gray-50/60 dark:hover:bg-neutral-800/40 transition-colors group">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full ${avatarColor(initial)} flex items-center justify-center text-white text-xs font-bold flex-shrink-0`}>
                              {initial}
                            </div>
                            <span className="text-sm font-semibold text-gray-800 dark:text-neutral-200">
                              {usuario.username}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-sm text-gray-700 dark:text-neutral-300 whitespace-nowrap">
                          {usuario.nome || <span className="text-gray-300 dark:text-neutral-600">—</span>}
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm text-gray-600 dark:text-neutral-400">{usuario.email}</span>
                            {usuario.email_confirmado && (
                              <svg className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20" title="E-mail confirmado">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                              </svg>
                            )}
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-sm text-gray-600 dark:text-neutral-400 whitespace-nowrap">
                          {getDepartmentLabel(usuario.department)}
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            usuario.role === 'admin'
                              ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300'
                              : usuario.role === 'supervisor'
                              ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                              : 'bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-neutral-400'
                          }`}>
                            {getRoleLabel(usuario.role)}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            usuario.ativo
                              ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                              : 'bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${usuario.ativo ? 'bg-emerald-500' : 'bg-red-500'}`}/>
                            {usuario.ativo ? 'Ativo' : 'Inativo'}
                          </span>
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => abrirModalEdicao(usuario)}
                              title="Editar"
                              className="p-1.5 rounded-lg text-gray-400 dark:text-neutral-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50 transition-colors"
                            >
                              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                              </svg>
                            </button>
                            {usuario.ativo ? (
                              <button
                                onClick={() => desativarUsuario(usuario)}
                                disabled={usuario.id === usuarioLogado?.id}
                                title={usuario.id === usuarioLogado?.id ? 'Não é possível desativar seu próprio usuário' : 'Desativar'}
                                className="p-1.5 rounded-lg text-gray-400 dark:text-neutral-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"/>
                                </svg>
                              </button>
                            ) : (
                              <button
                                onClick={() => ativarUsuario(usuario)}
                                title="Reativar"
                                className="p-1.5 rounded-lg text-gray-400 dark:text-neutral-500 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 transition-colors"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Modal Criar / Editar ── */}
      {modalAberto && (
        <div
          className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={fecharModal}
        >
          <div
            className="bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl w-full max-w-xl max-h-[92vh] overflow-y-auto border border-gray-100 dark:border-neutral-800"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Cabeçalho do Modal */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100 dark:border-neutral-800 sticky top-0 bg-white dark:bg-neutral-900 rounded-t-2xl z-10">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${modoEdicao ? 'bg-amber-100 dark:bg-amber-900/40' : 'bg-blue-100 dark:bg-blue-900/40'}`}>
                  {modoEdicao ? (
                    <svg className="w-4 h-4 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/>
                    </svg>
                  )}
                </div>
                <h2 className="text-base font-bold text-gray-900 dark:text-neutral-100">
                  {modoEdicao ? 'Editar Usuário' : 'Novo Usuário'}
                </h2>
              </div>
              <button
                onClick={fecharModal}
                className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-400 dark:text-neutral-500 hover:text-gray-600 dark:hover:text-neutral-300 hover:bg-gray-100 dark:hover:bg-neutral-800 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
              {/* Linha 1: Usuário + E-mail */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="username" className={labelCls}>Usuário *</label>
                  <input id="username" type="text" name="username" value={formData.username}
                    onChange={handleInputChange} placeholder="ex: ana.lima"
                    className={inputCls}/>
                </div>
                <div>
                  <label htmlFor="email" className={labelCls}>E-mail *</label>
                  <input id="email" type="email" name="email" value={formData.email}
                    onChange={handleInputChange} placeholder="ana@lab.com" className={inputCls}/>
                </div>
              </div>

              {/* Nome completo */}
              <div>
                <label htmlFor="nome" className={labelCls}>Nome Completo *</label>
                <input id="nome" type="text" name="nome" value={formData.nome}
                  onChange={handleInputChange} placeholder="Ana Lima da Silva" className={inputCls}/>
              </div>

              {/* Departamento + Perfil */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="department" className={labelCls}>Departamento *</label>
                  <select id="department" name="department" value={formData.department}
                    onChange={handleInputChange} className={inputCls}>
                    <option value="">Selecione...</option>
                    {DEPARTMENTS.map(dept => (
                      <option key={dept.id} value={dept.id}>{dept.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label htmlFor="role" className={labelCls}>Perfil *</label>
                  <select id="role" name="role" value={formData.role}
                    onChange={handleInputChange} className={inputCls}>
                    <option value="usuario">Usuário</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>
              </div>

              {/* Senha */}
              <div>
                <label htmlFor="senha" className={labelCls}>
                  Senha {modoEdicao ? <span className="normal-case font-normal text-gray-400 dark:text-neutral-500">(em branco = sem alteração)</span> : '*'}
                </label>
                <input id="senha" type="password" name="senha" value={formData.senha}
                  onChange={handleInputChange}
                  placeholder={modoEdicao ? 'Nova senha (opcional)' : 'Mínimo 6 caracteres'}
                  className={inputCls}/>
              </div>

              {/* Credenciais apLIS */}
              <div className="rounded-xl border border-gray-100 dark:border-neutral-800 bg-gray-50 dark:bg-neutral-800/50 p-4">
                <p className="text-xs font-semibold text-gray-500 dark:text-neutral-400 uppercase tracking-wide mb-3 flex items-center gap-2">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"/>
                  </svg>
                  Credenciais apLIS
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="aplis_usuario" className={labelCls}>Usuário apLIS</label>
                    <input id="aplis_usuario" type="text" name="aplis_usuario" value={formData.aplis_usuario}
                      onChange={handleInputChange} placeholder="ex: api.ana"
                      className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition"/>
                  </div>
                  <div>
                    <label htmlFor="aplis_senha" className={labelCls}>Senha apLIS</label>
                    <input id="aplis_senha" type="password" name="aplis_senha" value={formData.aplis_senha}
                      onChange={handleInputChange} placeholder="Senha do apLIS"
                      className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 transition"/>
                  </div>
                </div>
                <p className="text-xs text-gray-400 dark:text-neutral-500 mt-2">
                  Usadas para autenticar no sistema apLIS quando este usuário fizer login.
                </p>
              </div>

              {/* Alertas no modal */}
              {erro && (
                <div className="flex items-start gap-2.5 p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/60 text-red-700 dark:text-red-300 rounded-xl text-sm">
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
                  </svg>
                  {erro}
                </div>
              )}
              {sucesso && (
                <div className="flex items-start gap-2.5 p-3.5 bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-900/60 text-green-700 dark:text-green-300 rounded-xl text-sm">
                  <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  {sucesso}
                </div>
              )}

              {/* Botões */}
              <div className="flex gap-3 justify-end pt-2 border-t border-gray-100 dark:border-neutral-800">
                <button
                  type="button"
                  onClick={fecharModal}
                  className="px-4 py-2 text-sm font-semibold text-gray-600 dark:text-neutral-300 bg-gray-100 dark:bg-neutral-800 hover:bg-gray-200 dark:hover:bg-neutral-700 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-sm shadow-blue-600/25 transition-all"
                >
                  {modoEdicao ? 'Salvar Alterações' : 'Criar Usuário'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
