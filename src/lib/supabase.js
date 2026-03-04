import { createClient } from '@supabase/supabase-js'

// Obter as variáveis de ambiente
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'https://vwcfgbjuayeugcqrpbma.supabase.co'
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3Y2ZnYmp1YXlldWdjcXJwYm1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODIzMDksImV4cCI6MjA4NDc1ODMwOX0.xZp11S9oUvg8D4MKfcIyw_L2H3oQO7jiETEfA_43A0M'
const supabaseServiceKey = process.env.REACT_APP_SUPABASE_SERVICE_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3Y2ZnYmp1YXlldWdjcXJwYm1hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MjMwOSwiZXhwIjoyMDg0NzU4MzA5fQ.1gYpOjRsZyGiLSvafw74CeufaAOP_LlGMsEHjFIvIQI'

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
      persistSession: false,
      storageKey: 'sb-admin-auth-token'
    }
  }
)
