"""
API de Autenticação
Endpoints para login, logout e gerenciamento de usuários
"""

from flask import Blueprint, request, jsonify
from auth import (
    autenticar_usuario,
    criar_usuario,
    listar_usuarios,
    atualizar_usuario,
    deletar_usuario,
    token_required,
    admin_required
)
import logging

logger = logging.getLogger(__name__)

# Criar Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# ============================================
# ENDPOINTS PÚBLICOS (SEM AUTENTICAÇÃO)
# ============================================

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login de usuário

    Request Body:
        {
            "username": "admin",
            "senha": "admin123"
        }

    Response:
        {
            "sucesso": 1,
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "usuario": {
                "id": "...",
                "username": "admin",
                "email": "admin@lab.com",
                "nome_completo": "Administrador",
                "role": "admin"
            }
        }
    """
    try:
        dados = request.json

        username = dados.get('username')
        senha = dados.get('senha')

        if not username or not senha:
            return jsonify({'sucesso': 0, 'erro': 'Username e senha são obrigatórios'}), 400

        resultado = autenticar_usuario(username, senha)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 401

    except Exception as e:
        logger.error(f"[API_AUTH] Erro no login: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao processar login'}), 500


@auth_bp.route('/registro', methods=['POST'])
def registro_primeiro_acesso():
    """
    Registro de novo usuário (Primeiro Acesso)
    PÚBLICO - Não requer autenticação
    Todos os usuários criados por este endpoint terão role "usuario"

    Request Body:
        {
            "username": "joao",
            "email": "joao@lab.com",
            "senha": "senha123",
            "nome_completo": "João Silva",
            "telefone": "(61) 99999-9999" (opcional)
        }

    Response:
        {
            "sucesso": 1,
            "mensagem": "Usuário criado com sucesso",
            "usuario": {
                "id": "...",
                "username": "joao",
                "email": "joao@lab.com",
                "nome_completo": "João Silva",
                "role": "usuario"
            }
        }
    """
    try:
        dados = request.json

        # Validar campos obrigatórios
        username = dados.get('username')
        email = dados.get('email')
        senha = dados.get('senha')
        nome_completo = dados.get('nome_completo')

        if not all([username, email, senha, nome_completo]):
            return jsonify({
                'sucesso': 0,
                'erro': 'Username, email, senha e nome completo são obrigatórios'
            }), 400

        # Forçar role como "usuario" para primeiro acesso
        dados['role'] = 'usuario'
        dados['ativo'] = True

        # Criar usuário
        resultado = criar_usuario(dados)

        if resultado['sucesso'] == 1:
            logger.info(f"[API_AUTH] Novo usuário registrado (primeiro acesso): {username}")
            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro no registro: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao processar registro'}), 500


@auth_bp.route('/verificar', methods=['GET'])
@token_required
def verificar_token(usuario_atual):
    """
    Verifica se o token é válido e retorna dados do usuário

    Headers:
        Authorization: Bearer <token>

    Response:
        {
            "sucesso": 1,
            "usuario": {
                "id": "...",
                "username": "admin",
                "nome_completo": "Administrador",
                "role": "admin"
            }
        }
    """
    try:
        # Remover senha_hash
        usuario_atual.pop('senha_hash', None)

        return jsonify({
            'sucesso': 1,
            'usuario': usuario_atual
        }), 200

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao verificar token: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao verificar token'}), 500


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(usuario_atual):
    """
    Logout do usuário (apenas registra no log)

    Headers:
        Authorization: Bearer <token>

    Response:
        {
            "sucesso": 1,
            "mensagem": "Logout realizado com sucesso"
        }
    """
    try:
        from supabase_client import supabase_manager

        # Registrar logout no log
        try:
            supabase_manager.client.table('log_atividades') \
                .insert({
                    'usuario_id': usuario_atual['id'],
                    'acao': 'logout',
                    'descricao': f'Logout: {usuario_atual["username"]}',
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent')
                }) \
                .execute()
        except:
            pass

        logger.info(f"[API_AUTH] Logout: {usuario_atual['username']}")

        return jsonify({
            'sucesso': 1,
            'mensagem': 'Logout realizado com sucesso'
        }), 200

    except Exception as e:
        logger.error(f"[API_AUTH] Erro no logout: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao processar logout'}), 500


# ============================================
# ENDPOINTS PROTEGIDOS (REQUEREM AUTENTICAÇÃO)
# ============================================

@auth_bp.route('/perfil', methods=['GET'])
@token_required
def obter_perfil(usuario_atual):
    """
    Retorna perfil do usuário autenticado

    Headers:
        Authorization: Bearer <token>
    """
    usuario_atual.pop('senha_hash', None)

    return jsonify({
        'sucesso': 1,
        'usuario': usuario_atual
    }), 200


@auth_bp.route('/perfil', methods=['PUT'])
@token_required
def atualizar_perfil(usuario_atual):
    """
    Atualiza perfil do usuário autenticado

    Headers:
        Authorization: Bearer <token>

    Request Body:
        {
            "nome_completo": "Novo Nome",
            "email": "novo@email.com",
            "telefone": "(61) 99999-9999",
            "nova_senha": "senha123" (opcional)
        }
    """
    try:
        dados = request.json

        # Não permitir alterar role do próprio perfil
        dados.pop('role', None)
        dados.pop('ativo', None)

        resultado = atualizar_usuario(usuario_atual['id'], dados)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao atualizar perfil: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao atualizar perfil'}), 500


# ============================================
# ENDPOINTS DE ADMIN (REQUEREM ADMIN)
# ============================================

@auth_bp.route('/usuarios', methods=['GET'])
@admin_required
def listar_todos_usuarios(usuario_atual):
    """
    Lista todos os usuários (apenas admin)

    Headers:
        Authorization: Bearer <token>

    Response:
        {
            "sucesso": 1,
            "usuarios": [...],
            "total": 10
        }
    """
    try:
        resultado = listar_usuarios()
        return jsonify(resultado), 200

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao listar usuários: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao listar usuários'}), 500


@auth_bp.route('/usuarios', methods=['POST'])
@admin_required
def criar_novo_usuario(usuario_atual):
    """
    Cria um novo usuário (apenas admin)

    Headers:
        Authorization: Bearer <token>

    Request Body:
        {
            "username": "joao",
            "email": "joao@lab.com",
            "senha": "senha123",
            "nome_completo": "João Silva",
            "role": "usuario",
            "cpf": "12345678900",
            "telefone": "(61) 99999-9999"
        }
    """
    try:
        dados = request.json

        username = dados.get('username')
        email = dados.get('email')
        senha = dados.get('senha')
        nome_completo = dados.get('nome_completo')
        role = dados.get('role', 'usuario')
        cpf = dados.get('cpf')
        telefone = dados.get('telefone')

        resultado = criar_usuario(
            username=username,
            email=email,
            senha=senha,
            nome_completo=nome_completo,
            role=role,
            cpf=cpf,
            telefone=telefone,
            criado_por=usuario_atual['username']
        )

        if resultado['sucesso'] == 1:
            # Registrar no log
            try:
                from supabase_client import supabase_manager
                supabase_manager.client.table('log_atividades') \
                    .insert({
                        'usuario_id': usuario_atual['id'],
                        'acao': 'criar_usuario',
                        'descricao': f'Criou usuário: {username}',
                        'ip_address': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent')
                    }) \
                    .execute()
            except:
                pass

            return jsonify(resultado), 201
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao criar usuário: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao criar usuário'}), 500


@auth_bp.route('/usuarios/<usuario_id>', methods=['PUT'])
@admin_required
def atualizar_usuario_admin(usuario_atual, usuario_id):
    """
    Atualiza um usuário (apenas admin)

    Headers:
        Authorization: Bearer <token>

    Request Body:
        {
            "nome_completo": "João Silva Santos",
            "email": "joao@lab.com",
            "role": "supervisor",
            "ativo": true
        }
    """
    try:
        dados = request.json

        resultado = atualizar_usuario(usuario_id, dados)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao atualizar usuário: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao atualizar usuário'}), 500


@auth_bp.route('/usuarios/<usuario_id>', methods=['DELETE'])
@admin_required
def deletar_usuario_admin(usuario_atual, usuario_id):
    """
    Desativa um usuário (apenas admin)

    Headers:
        Authorization: Bearer <token>
    """
    try:
        # Não permitir deletar a si mesmo
        if usuario_id == usuario_atual['id']:
            return jsonify({'sucesso': 0, 'erro': 'Não é possível desativar seu próprio usuário'}), 400

        resultado = deletar_usuario(usuario_id)

        if resultado['sucesso'] == 1:
            return jsonify(resultado), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao deletar usuário: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao deletar usuário'}), 500


@auth_bp.route('/usuarios/<usuario_id>/ativar', methods=['POST'])
@admin_required
def ativar_usuario_admin(usuario_atual, usuario_id):
    """
    Reativa um usuário desativado (apenas admin)

    Headers:
        Authorization: Bearer <token>
    """
    try:
        resultado = atualizar_usuario(usuario_id, {'ativo': True})

        if resultado['sucesso'] == 1:
            return jsonify({
                'sucesso': 1,
                'mensagem': 'Usuário ativado com sucesso',
                'usuario': resultado['usuario']
            }), 200
        else:
            return jsonify(resultado), 400

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao ativar usuário: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao ativar usuário'}), 500


# ============================================
# ESTATÍSTICAS E LOGS (APENAS ADMIN)
# ============================================

@auth_bp.route('/estatisticas', methods=['GET'])
@admin_required
def obter_estatisticas(usuario_atual):
    """
    Retorna estatísticas do sistema (apenas admin)

    Headers:
        Authorization: Bearer <token>
    """
    try:
        from supabase_client import supabase_manager

        # Total de usuários
        usuarios_result = supabase_manager.client.table('usuarios') \
            .select('id, ativo', count='exact') \
            .execute()

        total_usuarios = len(usuarios_result.data)
        usuarios_ativos = len([u for u in usuarios_result.data if u['ativo']])

        # Usuários por role
        usuarios_por_role = {}
        for usuario in usuarios_result.data:
            role = usuario.get('role', 'usuario')
            usuarios_por_role[role] = usuarios_por_role.get(role, 0) + 1

        # Atividades recentes
        atividades_result = supabase_manager.client.table('log_atividades') \
            .select('*') \
            .order('created_at', desc=True) \
            .limit(10) \
            .execute()

        return jsonify({
            'sucesso': 1,
            'estatisticas': {
                'total_usuarios': total_usuarios,
                'usuarios_ativos': usuarios_ativos,
                'usuarios_inativos': total_usuarios - usuarios_ativos,
                'usuarios_por_role': usuarios_por_role,
                'atividades_recentes': atividades_result.data
            }
        }), 200

    except Exception as e:
        logger.error(f"[API_AUTH] Erro ao obter estatísticas: {e}")
        return jsonify({'sucesso': 0, 'erro': 'Erro ao obter estatísticas'}), 500
