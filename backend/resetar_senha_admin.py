"""
Script para resetar a senha do usuário admin
"""

from supabase_client import supabase_manager
from auth import hash_senha
import bcrypt

def verificar_e_resetar_admin():
    """Verifica o usuário admin e reseta a senha"""
    print("=" * 80)
    print("RESETANDO SENHA DO ADMIN")
    print("=" * 80)

    try:
        # Buscar usuário admin
        result = supabase_manager.client.table('usuarios') \
            .select('*') \
            .eq('username', 'admin') \
            .execute()

        if not result.data or len(result.data) == 0:
            print("[INFO] Usuário admin não existe. Criando...")
            from auth import criar_usuario
            import os

            # ⚠️ SENHA PADRÃO - ALTERE IMEDIATAMENTE APÓS CRIAR
            senha_admin = os.getenv('ADMIN_DEFAULT_PASSWORD', 'Admin@123!Change')
            
            resultado = criar_usuario(
                username='admin',
                email='admin@lab.com',
                senha=senha_admin,
                nome_completo='Administrador do Sistema',
                role='admin',
                criado_por='sistema'
            )

            if resultado['sucesso'] == 1:
                print("[OK] Usuário admin criado!")
                print("  Username: admin")
                print("  Senha: admin123")
            else:
                print(f"[ERRO] {resultado.get('erro')}")
            return

        # Usuário existe, vamos resetar a senha
        usuario = result.data[0]
        print(f"\n[INFO] Usuário encontrado:")
        print(f"  ID: {usuario.get('id')}")
        print(f"  Username: {usuario.get('username')}")
        print(f"  Email: {usuario.get('email')}")
        print(f"  Role: {usuario.get('role')}")
        print(f"  Ativo: {usuario.get('ativo')}")

        # Testar senha atual
        print("\n[INFO] Testando senha atual 'admin123'...")
        senha_atual = usuario.get('senha_hash')

        try:
            senha_bytes = 'admin123'.encode('utf-8')
            hash_bytes = senha_atual.encode('utf-8')
            senha_ok = bcrypt.checkpw(senha_bytes, hash_bytes)

            if senha_ok:
                print("[OK] A senha 'admin123' já está correta!")
                print("\nPara fazer login:")
                print("  Username: admin")
                print("  Senha: admin123")
                return
            else:
                print("[AVISO] A senha atual não é 'admin123'")
        except Exception as e:
            print(f"[AVISO] Erro ao verificar senha: {e}")

        # Resetar senha
        print("\n[INFO] Resetando senha para 'admin123'...")
        nova_senha_hash = hash_senha('admin123')

        update_result = supabase_manager.client.table('usuarios') \
            .update({'senha_hash': nova_senha_hash}) \
            .eq('id', usuario.get('id')) \
            .execute()

        if update_result.data and len(update_result.data) > 0:
            print("[OK] Senha resetada com sucesso!")
            print("\nPara fazer login:")
            print("  Username: admin")
            print("  Senha: admin123")
        else:
            print("[ERRO] Falha ao resetar senha")

    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verificar_e_resetar_admin()
