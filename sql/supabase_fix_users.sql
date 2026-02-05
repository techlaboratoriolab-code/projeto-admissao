-- ============================================
-- SCRIPT PARA CORRIGIR REGISTRO DE USUÁRIOS
-- ============================================

-- 1. Criar tabela de usuários (se não existir)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    username TEXT,
    avatar_url TEXT,
    lab_points INTEGER DEFAULT 0,
    role TEXT DEFAULT 'usuario',
    department TEXT DEFAULT 'operações',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Habilitar RLS (Row Level Security)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 3. Criar políticas de acesso
DROP POLICY IF EXISTS "Usuários podem ver todos os perfis" ON public.users;
CREATE POLICY "Usuários podem ver todos os perfis"
    ON public.users FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Usuários podem atualizar seu próprio perfil" ON public.users;
CREATE POLICY "Usuários podem atualizar seu próprio perfil"
    ON public.users FOR UPDATE
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Service role pode fazer tudo" ON public.users;
CREATE POLICY "Service role pode fazer tudo"
    ON public.users FOR ALL
    USING (auth.role() = 'service_role');

-- 4. Criar função que insere usuário automaticamente
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (
        id,
        email,
        nome,
        username,
        department,
        role,
        lab_points,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nome', NEW.raw_user_meta_data->>'name', NEW.email),
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'department', 'operações'),
        COALESCE(NEW.raw_user_meta_data->>'role', 'usuario'),
        0,
        NOW(),
        NOW()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. Remover trigger antigo se existir e criar novo
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 6. Criar função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS on_user_updated ON public.users;
CREATE TRIGGER on_user_updated
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 7. Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE '✅ Tabela e triggers criados com sucesso!';
    RAISE NOTICE '📝 Agora você pode criar usuários normalmente.';
END $$;
