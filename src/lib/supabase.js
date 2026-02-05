import { createClient } from '@supabase/supabase-js'

// ⚠️ IMPORTANTE: Configure as variáveis de ambiente no arquivo .env
// Nunca commite chaves do Supabase no código!
const supabaseUrl = process.env.REACT_APP_SUPABASE_URL
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY

// Validação: garantir que as variáveis estão configuradas
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('❌ ERRO: Configure REACT_APP_SUPABASE_URL e REACT_APP_SUPABASE_ANON_KEY no arquivo .env')
}

console.log('🔍 SUPABASE CONFIG:')
console.log('URL:', supabaseUrl ? '✅ Configurado' : '❌ Não configurado')
console.log('Anon Key:', supabaseAnonKey ? '✅ Configurado' : '❌ Não configurado')

// Cliente normal (para usuários)
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: false
  }
})

// ⚠️ NOTA: Service role key NÃO deve ser exposta no frontend!
// Em produção, operações admin devem ser feitas pelo backend.
// Por segurança, não exportamos supabaseAdmin no frontend.
export const supabaseAdmin = null // Removido por segurança
    autoRefreshToken: false
  }
})
