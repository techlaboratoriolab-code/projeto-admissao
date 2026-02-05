-- ============================================
-- PROMOVER USUÁRIO A ADMINISTRADOR
-- ============================================
-- Use este script para dar permissões de admin a um usuário existente

-- IMPORTANTE: Substitua o email pelo email do usuário que deseja promover
-- Exemplo: tech.laboratorio.lab@gmail.com

-- 1️⃣ PROMOVER USUÁRIO A ADMIN (substituir o email)
UPDATE auth.users
SET 
  raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'::jsonb),
    '{role}',
    '"admin"'
  )
WHERE email = 'tech.laboratorio.lab@gmail.com';  -- ⬅️ ALTERE ESTE EMAIL

-- 2️⃣ VERIFICAR SE A ATUALIZAÇÃO FUNCIONOU
SELECT 
  id,
  email,
  raw_user_meta_data->>'username' as username,
  raw_user_meta_data->>'name' as nome,
  raw_user_meta_data->>'role' as role,
  raw_user_meta_data->>'department' as department,
  email_confirmed_at,
  created_at
FROM auth.users
WHERE email = 'tech.laboratorio.lab@gmail.com'  -- ⬅️ ALTERE ESTE EMAIL
ORDER BY created_at DESC;

-- ============================================
-- EXEMPLO DE USO:
-- ============================================

-- Se você quiser promover o usuário 'joao@lab.com', faça:
/*
UPDATE auth.users
SET 
  raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'::jsonb),
    '{role}',
    '"admin"'
  )
WHERE email = 'joao@lab.com';
*/

-- ============================================
-- PROMOVER VÁRIOS USUÁRIOS DE UMA VEZ:
-- ============================================

-- Se quiser promover múltiplos usuários, use IN:
/*
UPDATE auth.users
SET 
  raw_user_meta_data = jsonb_set(
    COALESCE(raw_user_meta_data, '{}'::jsonb),
    '{role}',
    '"admin"'
  )
WHERE email IN (
  'usuario1@lab.com',
  'usuario2@lab.com',
  'usuario3@lab.com'
);
*/

-- ============================================
-- REMOVER PERMISSÃO DE ADMIN (downgrade):
-- ============================================

-- Para voltar um admin para usuário comum:
/*
UPDATE auth.users
SET 
  raw_user_meta_data = jsonb_set(
    raw_user_meta_data,
    '{role}',
    '"usuario"'
  )
WHERE email = 'usuario@lab.com';
*/

-- ============================================
-- LISTAR TODOS OS ADMINISTRADORES:
-- ============================================

SELECT 
  id,
  email,
  raw_user_meta_data->>'username' as username,
  raw_user_meta_data->>'name' as nome,
  raw_user_meta_data->>'department' as department,
  email_confirmed_at,
  created_at
FROM auth.users
WHERE raw_user_meta_data->>'role' = 'admin'
ORDER BY created_at DESC;

-- ============================================
-- LISTAR TODOS OS USUÁRIOS POR ROLE:
-- ============================================

SELECT 
  raw_user_meta_data->>'role' as role,
  COUNT(*) as total
FROM auth.users
GROUP BY raw_user_meta_data->>'role'
ORDER BY total DESC;
