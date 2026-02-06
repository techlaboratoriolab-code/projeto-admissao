import { createClient } from '@supabase/supabase-js'

// Obter as variáveis de ambiente
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'CONFIGURE_SUPABASE_URL_NO_ENV'
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'CONFIGURE_SUPABASE_ANON_KEY_NO_ENV'
const supabaseServiceKey = process.env.REACT_APP_SUPABASE_SERVICE_KEY || 'CONFIGURE_SUPABASE_SERVICE_KEY_NO_ENV'

// Validação: garantir que as variáveis estão configuradas
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ ERRO: Configure REACT_APP_SUPABASE_URL e REACT_APP_SUPABASE_ANON_KEY no arquivo .env')
}

console.log('🔍 SUPABASE CONFIG:')
console.log('URL:', supabaseUrl ? '✅ Configurado' : '❌ Não configurado')
console.log('Anon Key:', supabaseAnonKey ? '✅ Configurado' : '❌ Não configurado')
console.log('Service Key:', supabaseServiceKey ? '✅ Configurado' : '❌ Não configurado')

// Cliente normal (para usuários)
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false
  }
})

// Supabase Admin (para gerenciamento de usuários)
// ⚠️ IMPORTANTE: Em produção, essas operações devem ser movidas para o backend
export const supabaseAdmin = createClient(
  supabaseUrl,
  supabaseServiceKey,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  }
)
