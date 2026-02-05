-- ============================================
-- DESABILITAR CONFIRMAÇÃO DE EMAIL
-- ============================================

-- Confirmar todos os usuários existentes automaticamente
UPDATE auth.users 
SET email_confirmed_at = NOW()
WHERE email_confirmed_at IS NULL;

-- Verificar quantos usuários foram confirmados
SELECT 
    'Usuários confirmados:' as mensagem,
    COUNT(*) as total
FROM auth.users
WHERE email_confirmed_at IS NOT NULL;
