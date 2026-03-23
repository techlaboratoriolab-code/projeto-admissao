/**
 * Wrapper para Supabase Admin REST API.
 *
 * O cliente supabase-js v2 bloqueia auth.admin.* no browser.
 * Esta lib faz as mesmas chamadas via fetch direto para a API REST,
 * contornando essa limitação de forma oficial e segura.
 */

const SUPABASE_URL = process.env.REACT_APP_SUPABASE_URL || 'https://vwcfgbjuayeugcqrpbma.supabase.co';
const SERVICE_KEY  = process.env.REACT_APP_SUPABASE_SERVICE_KEY ||
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ3Y2ZnYmp1YXlldWdjcXJwYm1hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTE4MjMwOSwiZXhwIjoyMDg0NzU4MzA5fQ.1gYpOjRsZyGiLSvafw74CeufaAOP_LlGMsEHjFIvIQI';

const AUTH_BASE = `${SUPABASE_URL}/auth/v1/admin`;

const headers = {
  'apikey': SERVICE_KEY,
  'Authorization': `Bearer ${SERVICE_KEY}`,
  'Content-Type': 'application/json',
};

async function adminFetch(path, options = {}) {
  const res = await fetch(`${AUTH_BASE}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });
  const json = await res.json();
  if (!res.ok) {
    throw new Error(json.msg || json.message || `HTTP ${res.status}`);
  }
  return json;
}

// ─── Listar todos os usuários ────────────────────────────────────────────────
export async function adminListUsers() {
  // Supabase retorna { users: [], aud: '...' }
  const data = await adminFetch('/users?per_page=1000');
  return data.users || [];
}

// ─── Criar usuário ───────────────────────────────────────────────────────────
export async function adminCreateUser({ email, password, user_metadata }) {
  return adminFetch('/users', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      email_confirm: true,
      user_metadata: user_metadata || {},
    }),
  });
}

// ─── Atualizar usuário ───────────────────────────────────────────────────────
export async function adminUpdateUser(id, updates) {
  return adminFetch(`/users/${id}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

// ─── Banir / desbanir usuário ────────────────────────────────────────────────
export async function adminBanUser(id) {
  return adminUpdateUser(id, { ban_duration: '876000h' }); // ~100 anos
}

export async function adminUnbanUser(id) {
  return adminUpdateUser(id, { ban_duration: 'none' });
}
