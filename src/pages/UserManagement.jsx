import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { supabaseAdmin } from '../lib/supabase';
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

      // Buscar usuários do Supabase Auth
      const { data: { users }, error } = await supabaseAdmin.auth.admin.listUsers();

      if (error) {
        setErro('Erro ao carregar usuários: ' + error.message);
        return;
      }

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
      if (modoEdicao) {
        // ATUALIZAR USUÁRIO via Supabase Admin
        const updateData = {
          email: formData.email,
          user_metadata: {
            username: formData.username,
            name: formData.nome,
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

        const { error } = await supabaseAdmin.auth.admin.updateUserById(
          usuarioEditando.id,
          updateData
        );

        if (error) {
          setErro('Erro ao atualizar: ' + error.message);
          return;
        }

        setSucesso('✅ Usuário atualizado com sucesso!');
      } else {
        // CRIAR NOVO USUÁRIO via Supabase Admin
        const { data, error } = await supabaseAdmin.auth.admin.createUser({
          email: formData.email,
          password: formData.senha,
          email_confirm: true, // Auto-confirmar email
          user_metadata: {
            username: formData.username,
            name: formData.nome,
            department: formData.department,
            role: formData.role,
            aplis_usuario: formData.aplis_usuario || null,
            aplis_senha: formData.aplis_senha || null
          }
        });

        if (error) {
          setErro('Erro ao criar usuário: ' + error.message);
          return;
        }

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
      // Banir usuário no Supabase (bane por 100 anos = permanente)
      const { error } = await supabaseAdmin.auth.admin.updateUserById(
        usuario.id,
        { ban_duration: '876000h' } // ~100 anos
      );

      if (error) {
        setErro('Erro ao desativar: ' + error.message);
        return;
      }

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
      // Remover banimento do usuário
      const { error } = await supabaseAdmin.auth.admin.updateUserById(
        usuario.id,
        { ban_duration: 'none' }
      );

      if (error) {
        setErro('Erro ao reativar: ' + error.message);
        return;
      }

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

  const getRoleBadgeClass = (role) => {
    switch (role) {
      case 'admin': return 'badge-admin';
      case 'supervisor': return 'badge-supervisor';
      case 'usuario': return 'badge-usuario';
      default: return 'badge-default';
    }
  };

  const getRoleLabel = (role) => {
    switch (role) {
      case 'admin': return 'Administrador';
      case 'supervisor': return 'Supervisor';
      case 'usuario': return 'Usuário';
      default: return role;
    }
  };

  const formatarData = (dataISO) => {
    if (!dataISO) return 'Nunca';
    const data = new Date(dataISO);
    return data.toLocaleString('pt-BR');
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

  if (carregando) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 dark:bg-neutral-950">
        <div className="text-lg text-gray-600 dark:text-neutral-400">Carregando usuários...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-neutral-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-neutral-100">Gerenciamento de Usuários</h1>
            <p className="text-gray-600 dark:text-neutral-400 mt-1">Gerencie usuários, permissões e departamentos do sistema</p>
          </div>
          <button 
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg hover:shadow-lg transition-all font-medium flex items-center gap-2"
            onClick={abrirModalNovo}
          >
            <span className="text-xl">+</span>
            Novo Usuário
          </button>
        </div>

        {/* Mensagens de feedback */}
        {erro && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 rounded-lg">
            {erro}
          </div>
        )}

        {sucesso && (
          <div className="mb-6 p-4 bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-900/50 text-green-700 dark:text-green-300 rounded-lg">
            {sucesso}
          </div>
        )}

        {/* Estatísticas */}
        {estatisticas && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 p-6 border-l-4 border-blue-500 dark:border-blue-400">
              <div className="text-3xl font-bold text-gray-800 dark:text-neutral-100 mb-2">{estatisticas.total_usuarios}</div>
              <div className="text-sm text-gray-600 dark:text-neutral-400 font-medium">Total de Usuários</div>
            </div>
            <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 p-6 border-l-4 border-green-500 dark:border-green-400">
              <div className="text-3xl font-bold text-gray-800 dark:text-neutral-100 mb-2">{estatisticas.usuarios_ativos}</div>
              <div className="text-sm text-gray-600 dark:text-neutral-400 font-medium">Usuários Ativos</div>
            </div>
            <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 p-6 border-l-4 border-purple-500 dark:border-purple-400">
              <div className="text-3xl font-bold text-gray-800 dark:text-neutral-100 mb-2">{estatisticas.total_admins}</div>
              <div className="text-sm text-gray-600 dark:text-neutral-400 font-medium">Administradores</div>
            </div>
            <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 p-6 border-l-4 border-amber-500 dark:border-amber-400">
              <div className="text-3xl font-bold text-gray-800 dark:text-neutral-100 mb-2">{estatisticas.total_supervisores}</div>
              <div className="text-sm text-gray-600 dark:text-neutral-400 font-medium">Supervisores</div>
            </div>
          </div>
        )}

        {/* Filtros */}
        <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-800 dark:text-neutral-100 mb-4">Filtros</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Buscar</label>
              <input
                type="text"
                placeholder="Nome, email ou usuário..."
                value={buscaTexto}
                onChange={(e) => setBuscaTexto(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Perfil</label>
              <select
                value={filtroRole}
                onChange={(e) => setFiltroRole(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100"
              >
                <option value="todos">Todos os perfis</option>
                <option value="admin">Administrador</option>
                <option value="supervisor">Supervisor</option>
                <option value="usuario">Usuário</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Departamento</label>
              <select
                value={filtroDepartamento}
                onChange={(e) => setFiltroDepartamento(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100"
              >
                <option value="todos">Todos os departamentos</option>
                {DEPARTMENTS.map(dept => (
                  <option key={dept.id} value={dept.id}>{dept.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Tabela de usuários */}
        <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md dark:shadow-neutral-900/50 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-neutral-800 bg-gray-50 dark:bg-neutral-800">
            <p className="text-sm text-gray-600 dark:text-neutral-400">
              Exibindo <strong>{usuariosFiltrados.length}</strong> de <strong>{usuarios.length}</strong> usuários
            </p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-gray-100 dark:bg-neutral-800 border-b border-gray-200 dark:border-neutral-700">
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Usuário</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Nome Completo</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">E-mail</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Departamento</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Perfil</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Status</th>
                <th className="px-6 py-4 text-left text-sm font-semibold text-gray-700 dark:text-neutral-300">Ações</th>
              </tr>
            </thead>
            <tbody>
              {usuariosFiltrados.length === 0 ? (
                <tr>
                  <td colSpan="7" className="text-center py-12 text-gray-500 dark:text-neutral-400">
                    {buscaTexto || filtroRole !== 'todos' || filtroDepartamento !== 'todos' 
                      ? 'Nenhum usuário encontrado com os filtros aplicados' 
                      : 'Nenhum usuário cadastrado'}
                  </td>
                </tr>
              ) : (
                usuariosFiltrados.map((usuario) => (
                  <tr key={usuario.id} className="border-b border-gray-100 dark:border-neutral-800 hover:bg-gray-50 dark:hover:bg-neutral-800/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
                          {usuario.nome?.charAt(0)?.toUpperCase() || usuario.username?.charAt(0)?.toUpperCase() || 'U'}
                        </div>
                        <strong className="text-gray-800 dark:text-neutral-200">{usuario.username}</strong>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-700 dark:text-neutral-300">{usuario.nome || '-'}</td>
                    <td className="px-6 py-4 text-gray-700 dark:text-neutral-300">
                      <div className="flex items-center gap-2">
                        {usuario.email}
                        {usuario.email_confirmado && (
                          <span className="text-green-500 text-xs" title="Email confirmado">✓</span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-700 dark:text-neutral-300 text-sm">
                      {getDepartmentLabel(usuario.department)}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                        usuario.role === 'admin' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300' :
                        usuario.role === 'supervisor' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300' :
                        'bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-neutral-300'
                      }`}>
                        {getRoleLabel(usuario.role)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                        usuario.ativo ? 'bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300' : 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300'
                      }`}>
                        {usuario.ativo ? 'Ativo' : 'Inativo'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button
                          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors text-sm font-medium"
                          onClick={() => abrirModalEdicao(usuario)}
                          title="Editar usuário"
                        >
                          Editar
                        </button>
                        {usuario.ativo ? (
                          <button
                            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={() => desativarUsuario(usuario)}
                            disabled={usuario.id === usuarioLogado?.id}
                            title={usuario.id === usuarioLogado?.id ? 'Você não pode desativar seu próprio usuário' : 'Desativar usuário'}
                          >
                            Desativar
                          </button>
                        ) : (
                          <button
                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors text-sm font-medium"
                            onClick={() => ativarUsuario(usuario)}
                            title="Reativar usuário"
                          >
                            Ativar
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal de Criar/Editar Usuário */}
      {modalAberto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 dark:bg-opacity-70 flex items-center justify-center z-50 p-4" onClick={fecharModal}>
          <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-2xl dark:shadow-neutral-950/50 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center p-6 border-b border-gray-200 dark:border-neutral-800 sticky top-0 bg-white dark:bg-neutral-900">
              <h2 className="text-2xl font-bold text-gray-800 dark:text-neutral-100">{modoEdicao ? 'Editar Usuário' : 'Novo Usuário'}</h2>
              <button className="text-gray-400 dark:text-neutral-500 hover:text-gray-600 dark:hover:text-neutral-300 text-3xl font-bold leading-none" onClick={fecharModal}>×</button>
            </div>

            <form onSubmit={handleSubmit} className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Usuário *</label>
                  <input
                    id="username"
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleInputChange}
                    placeholder="Digite o nome de usuário"
                    disabled={modoEdicao}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 disabled:bg-gray-100 dark:disabled:bg-neutral-800/50 disabled:cursor-not-allowed placeholder:text-gray-400 dark:placeholder:text-neutral-500"
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">E-mail *</label>
                  <input
                    id="email"
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleInputChange}
                    placeholder="usuario@exemplo.com"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500"
                  />
                </div>
              </div>

              <div className="mb-4">
                <label htmlFor="nome" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Nome Completo *</label>
                <input
                  id="nome"
                  type="text"
                  name="nome"
                  value={formData.nome}
                  onChange={handleInputChange}
                  placeholder="Digite o nome completo"
                  className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label htmlFor="department" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Departamento *</label>
                  <select
                    id="department"
                    name="department"
                    value={formData.department}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100"
                  >
                    <option value="">Selecione um departamento</option>
                    {DEPARTMENTS.map(dept => (
                      <option key={dept.id} value={dept.id}>{dept.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label htmlFor="role" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">Perfil *</label>
                  <select
                    id="role"
                    name="role"
                    value={formData.role}
                    onChange={handleInputChange}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100"
                  >
                    <option value="usuario">Usuário</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>
              </div>

              <div className="mb-4">
                <label htmlFor="senha" className="block text-sm font-medium text-gray-700 dark:text-neutral-300 mb-2">
                  Senha {modoEdicao ? '(deixe em branco para não alterar)' : '*'}
                </label>
                <input
                  id="senha"
                  type="password"
                  name="senha"
                  value={formData.senha}
                  onChange={handleInputChange}
                  placeholder={modoEdicao ? 'Nova senha (opcional)' : 'Digite a senha (mínimo 6 caracteres)'}
                  className="w-full px-4 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-gray-400 dark:placeholder:text-neutral-500"
                />
              </div>

              {/* 🆕 CAMPOS DE LOGIN DO APLIS */}
              <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-950/30 border-2 border-blue-200 dark:border-blue-900/50 rounded-lg">
                <h3 className="text-sm font-bold text-blue-900 dark:text-blue-300 mb-3 flex items-center gap-2">
                  🔐 Credenciais apLIS
                  <span className="text-xs font-normal text-blue-600 dark:text-blue-400">(Sistema Laboratorial)</span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="aplis_usuario" className="block text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
                      Usuário apLIS
                    </label>
                    <input
                      id="aplis_usuario"
                      type="text"
                      name="aplis_usuario"
                      value={formData.aplis_usuario}
                      onChange={handleInputChange}
                      placeholder="Ex: api.ana"
                      className="w-full px-4 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-blue-400 dark:placeholder:text-blue-500"
                    />
                  </div>
                  <div>
                    <label htmlFor="aplis_senha" className="block text-sm font-medium text-blue-900 dark:text-blue-300 mb-2">
                      Senha apLIS
                    </label>
                    <input
                      id="aplis_senha"
                      type="password"
                      name="aplis_senha"
                      value={formData.aplis_senha}
                      onChange={handleInputChange}
                      placeholder="Senha do apLIS"
                      className="w-full px-4 py-2 border border-blue-300 dark:border-blue-700 rounded-lg focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-neutral-800 text-gray-900 dark:text-neutral-100 placeholder:text-blue-400 dark:placeholder:text-blue-500"
                    />
                  </div>
                </div>
                <p className="text-xs text-blue-700 dark:text-blue-400 mt-2">
                  💡 Essas credenciais serão usadas para acessar o sistema apLIS quando este usuário fizer login
                </p>
              </div>

              {/* Mensagens dentro do modal */}
              {erro && (
                <div className="mb-4 p-4 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-300 rounded-lg">
                  {erro}
                </div>
              )}

              {sucesso && (
                <div className="mb-4 p-4 bg-green-50 dark:bg-green-950/50 border border-green-200 dark:border-green-900/50 text-green-700 dark:text-green-300 rounded-lg">
                  {sucesso}
                </div>
              )}

              <div className="flex gap-3 justify-end pt-4 border-t border-gray-200 dark:border-neutral-800">
                <button 
                  type="button" 
                  className="px-6 py-2 bg-gray-200 dark:bg-neutral-800 text-gray-700 dark:text-neutral-300 rounded-lg hover:bg-gray-300 dark:hover:bg-neutral-700 transition-colors font-medium"
                  onClick={fecharModal}
                >
                  Cancelar
                </button>
                <button 
                  type="submit" 
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg hover:shadow-lg transition-all font-medium"
                >
                  {modoEdicao ? 'Atualizar Usuário' : 'Criar Usuário'}
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
