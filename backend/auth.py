"""
Módulo de Autenticação
Sistema de login e gerenciamento de usuários
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from supabase_client import supabase_manager

logger = logging.getLogger(__name__)

# Chave secreta para JWT (deve estar no .env em produção)
JWT_SECRET = os.getenv('JWT_SECRET', 'sua-chave-secreta-super-segura-mude-isso-em-producao')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# ============================================
# FUNÇÕES DE HASH DE SENHA
# ============================================

def hash_senha(senha):
    """
    Cria hash bcrypt da senha

    Args:
        senha (str): Senha em texto plano

    Returns:
        str: Hash da senha
    """
    senha_bytes = senha.encode('utf-8')
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha_bytes, salt)
    return hash_bytes.decode('utf-8')


def verificar_senha(senha, senha_hash):
    """
    Verifica se a senha corresponde ao hash

    Args:
        senha (str): Senha em texto plano
        senha_hash (str): Hash armazenado no banco

    Returns:
        bool: True se a senha está correta
    """
    try:
        senha_bytes = senha.encode('utf-8')
        hash_bytes = senha_hash.encode('utf-8')
        return bcrypt.checkpw(senha_bytes, hash_bytes)
    except Exception as e:
        logger.error(f"[AUTH] Erro ao verificar senha: {e}")
        return False


# ============================================
# FUNÇÕES DE JWT
# ============================================

def criar_token(usuario_id, username, role):
    """
    Cria um JWT token para o usuário

    Args:
        usuario_id (str): ID do usuário
        username (str): Nome de usuário
        role (str): Papel do usuário (admin, supervisor, usuario)

    Returns:
        str: JWT token
    """
    payload = {
        'usuario_id': str(usuario_id),
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verificar_token(token):
    """
    Verifica e decodifica um JWT token

    Args:
        token (str): JWT token

    Returns:
        dict: Payload do token ou None se inválido
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[AUTH] Token expirado")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[AUTH] Token inválido: {e}")
        return None


# ============================================
# DECORADORES DE AUTENTICAÇÃO
# ============================================

def token_required(f):
    """
    Decorator para proteger rotas que requerem autenticação

    Uso:
        @app.route('/api/protegida')
        @token_required
        def rota_protegida(usuario_atual):
            return jsonify({'mensagem': f'Olá {usuario_atual["username"]}'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Buscar token no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Formato: "Bearer <token>"
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'erro': 'Formato de token inválido'}), 401

        if not token:
            return jsonify({'erro': 'Token não fornecido'}), 401

        # Verificar token
        payload = verificar_token(token)

        if not payload:
            return jsonify({'erro': 'Token inválido ou expirado'}), 401

        # Buscar usuário no banco
        try:
            result = supabase_manager.client.table('usuarios') \
                .select('*') \
                .eq('id', payload['usuario_id']) \
                .eq('ativo', True) \
                .execute()

            if not result.data or len(result.data) == 0:
                return jsonify({'erro': 'Usuário não encontrado ou inativo'}), 401

            usuario_atual = result.data[0]

            # Atualizar último acesso
            supabase_manager.client.table('usuarios') \
                .update({'ultimo_login': datetime.utcnow().isoformat()}) \
                .eq('id', payload['usuario_id']) \
                .execute()

        except Exception as e:
            logger.error(f"[AUTH] Erro ao buscar usuário: {e}")
            return jsonify({'erro': 'Erro ao verificar autenticação'}), 500

        # Passar usuário para a função
        return f(usuario_atual, *args, **kwargs)

    return decorated


def admin_required(f):
    """
    Decorator para proteger rotas que requerem acesso de admin

    Uso:
        @app.route('/api/admin/usuarios')
        @admin_required
        def gerenciar_usuarios(usuario_atual):
            return jsonify({'usuarios': []})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Buscar token no header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'erro': 'Formato de token inválido'}), 401

        if not token:
            return jsonify({'erro': 'Token não fornecido'}), 401

        # Verificar token
        payload = verificar_token(token)

        if not payload:
            return jsonify({'erro': 'Token inválido ou expirado'}), 401

        # Verificar se é admin
        if payload.get('role') != 'admin':
            return jsonify({'erro': 'Acesso negado. Apenas administradores.'}), 403

        # Buscar usuário no banco
        try:
            result = supabase_manager.client.table('usuarios') \
                .select('*') \
                .eq('id', payload['usuario_id']) \
                .eq('ativo', True) \
                .execute()

            if not result.data or len(result.data) == 0:
                return jsonify({'erro': 'Usuário não encontrado ou inativo'}), 401

            usuario_atual = result.data[0]

        except Exception as e:
            logger.error(f"[AUTH] Erro ao buscar usuário: {e}")
            return jsonify({'erro': 'Erro ao verificar autenticação'}), 500

        # Passar usuário para a função
        return f(usuario_atual, *args, **kwargs)

    return decorated


# ============================================
# FUNÇÕES DE GERENCIAMENTO DE USUÁRIOS
# ============================================

def criar_usuario(username, email, senha, nome_completo, role='usuario', cpf=None, telefone=None, criado_por=None):
    """
    Cria um novo usuário no sistema

    Args:
        username (str): Nome de usuário único
        email (str): Email único
        senha (str): Senha em texto plano (será hashada)
        nome_completo (str): Nome completo do usuário
        role (str): Papel do usuário (admin, supervisor, usuario)
        cpf (str, optional): CPF do usuário
        telefone (str, optional): Telefone do usuário
        criado_por (str, optional): Quem criou o usuário

    Returns:
        dict: {'sucesso': 1/0, 'usuario': {...} ou 'erro': '...'}
    """
    try:
        # Validar campos obrigatórios
        if not username or not email or not senha or not nome_completo:
            return {'sucesso': 0, 'erro': 'Campos obrigatórios faltando'}

        # Verificar se usuário já existe
        result = supabase_manager.client.table('usuarios') \
            .select('id') \
            .or_(f'username.eq.{username},email.eq.{email}') \
            .execute()

        if result.data and len(result.data) > 0:
            return {'sucesso': 0, 'erro': 'Usuário ou email já existe'}

        # Criar hash da senha
        senha_hash = hash_senha(senha)

        # Inserir usuário
        dados_usuario = {
            'username': username,
            'email': email,
            'senha_hash': senha_hash,
            'nome_completo': nome_completo,
            'role': role,
            'cpf': cpf,
            'telefone': telefone,
            'ativo': True,
            'criado_por': criado_por
        }

        result = supabase_manager.client.table('usuarios') \
            .insert(dados_usuario) \
            .execute()

        if result.data and len(result.data) > 0:
            usuario = result.data[0]
            # Remover senha_hash da resposta
            usuario.pop('senha_hash', None)

            logger.info(f"[AUTH] Usuário criado: {username}")
            return {'sucesso': 1, 'usuario': usuario}
        else:
            return {'sucesso': 0, 'erro': 'Erro ao criar usuário'}

    except Exception as e:
        logger.error(f"[AUTH] Erro ao criar usuário: {e}")
        return {'sucesso': 0, 'erro': str(e)}


def autenticar_usuario(username, senha):
    """
    Autentica um usuário e retorna um token JWT

    Args:
        username (str): Nome de usuário ou email
        senha (str): Senha em texto plano

    Returns:
        dict: {'sucesso': 1/0, 'token': '...', 'usuario': {...} ou 'erro': '...'}
    """
    try:
        # Buscar usuário por username ou email
        result = supabase_manager.client.table('usuarios') \
            .select('*') \
            .or_(f'username.eq.{username},email.eq.{username}') \
            .eq('ativo', True) \
            .execute()

        if not result.data or len(result.data) == 0:
            logger.warning(f"[AUTH] Tentativa de login falhou: usuário não encontrado - {username}")
            return {'sucesso': 0, 'erro': 'Usuário ou senha inválidos'}

        usuario = result.data[0]

        # Verificar senha
        if not verificar_senha(senha, usuario['senha_hash']):
            logger.warning(f"[AUTH] Tentativa de login falhou: senha incorreta - {username}")
            return {'sucesso': 0, 'erro': 'Usuário ou senha inválidos'}

        # Criar token
        token = criar_token(usuario['id'], usuario['username'], usuario['role'])

        # Atualizar último login
        supabase_manager.client.table('usuarios') \
            .update({'ultimo_login': datetime.utcnow().isoformat()}) \
            .eq('id', usuario['id']) \
            .execute()

        # Registrar log de atividade
        try:
            supabase_manager.client.table('log_atividades') \
                .insert({
                    'usuario_id': usuario['id'],
                    'acao': 'login',
                    'descricao': f'Login bem-sucedido: {username}',
                    'ip_address': request.remote_addr if request else None,
                    'user_agent': request.headers.get('User-Agent') if request else None
                }) \
                .execute()
        except:
            pass  # Não falhar o login se o log der erro

        # Remover senha_hash da resposta
        usuario.pop('senha_hash', None)

        logger.info(f"[AUTH] Login bem-sucedido: {username}")

        return {
            'sucesso': 1,
            'token': token,
            'usuario': usuario
        }

    except Exception as e:
        logger.error(f"[AUTH] Erro ao autenticar usuário: {e}")
        return {'sucesso': 0, 'erro': 'Erro ao processar login'}


def listar_usuarios():
    """
    Lista todos os usuários do sistema

    Returns:
        dict: {'sucesso': 1/0, 'usuarios': [...] ou 'erro': '...'}
    """
    try:
        result = supabase_manager.client.table('usuarios') \
            .select('id, username, email, nome_completo, cpf, telefone, role, ativo, ultimo_login, created_at') \
            .order('created_at', desc=True) \
            .execute()

        return {
            'sucesso': 1,
            'usuarios': result.data,
            'total': len(result.data)
        }

    except Exception as e:
        logger.error(f"[AUTH] Erro ao listar usuários: {e}")
        return {'sucesso': 0, 'erro': str(e)}


def atualizar_usuario(usuario_id, dados):
    """
    Atualiza dados de um usuário

    Args:
        usuario_id (str): ID do usuário
        dados (dict): Campos a serem atualizados

    Returns:
        dict: {'sucesso': 1/0, 'usuario': {...} ou 'erro': '...'}
    """
    try:
        # Não permitir atualizar senha_hash diretamente
        dados.pop('senha_hash', None)
        dados.pop('id', None)

        # Se tiver nova senha, criar hash
        if 'nova_senha' in dados:
            dados['senha_hash'] = hash_senha(dados['nova_senha'])
            dados.pop('nova_senha')

        result = supabase_manager.client.table('usuarios') \
            .update(dados) \
            .eq('id', usuario_id) \
            .execute()

        if result.data and len(result.data) > 0:
            usuario = result.data[0]
            usuario.pop('senha_hash', None)
            return {'sucesso': 1, 'usuario': usuario}
        else:
            return {'sucesso': 0, 'erro': 'Usuário não encontrado'}

    except Exception as e:
        logger.error(f"[AUTH] Erro ao atualizar usuário: {e}")
        return {'sucesso': 0, 'erro': str(e)}


def deletar_usuario(usuario_id):
    """
    Desativa um usuário (soft delete)

    Args:
        usuario_id (str): ID do usuário

    Returns:
        dict: {'sucesso': 1/0, 'mensagem': '...' ou 'erro': '...'}
    """
    try:
        result = supabase_manager.client.table('usuarios') \
            .update({'ativo': False}) \
            .eq('id', usuario_id) \
            .execute()

        if result.data and len(result.data) > 0:
            return {'sucesso': 1, 'mensagem': 'Usuário desativado com sucesso'}
        else:
            return {'sucesso': 0, 'erro': 'Usuário não encontrado'}

    except Exception as e:
        logger.error(f"[AUTH] Erro ao deletar usuário: {e}")
        return {'sucesso': 0, 'erro': str(e)}
