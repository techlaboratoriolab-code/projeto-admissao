/**
 * Configuração da API
 *
 * MODOS DE ACESSO:
 *
 * 1. LOCALHOST (apenas na sua máquina):
 *    USE_NETWORK = false, USE_NGROK = false
 *
 * 2. REDE LOCAL (outras pessoas na mesma rede WiFi/LAN):
 *    USE_NETWORK = true, USE_NGROK = false
 *    IMPORTANTE: Configure seu IP local em NETWORK_IP abaixo!
 *
 * 3. INTERNET (qualquer lugar do mundo via ngrok):
 *    USE_NGROK = true
 */

// Em produção no Vercel, sempre usar proxy same-origin (/api) para evitar CORS com ngrok.
const isVercelHost =
  typeof window !== 'undefined' && window.location.hostname.endsWith('vercel.app');

// URL do backend — em Vercel força /api; local segue env/fallback localhost.
export const API_BASE_URL = isVercelHost
  ? '/api'
  : (process.env.REACT_APP_API_URL || 'http://localhost:5000');

// Wrapper do fetch que adiciona headers necessários para o ngrok
export const apiFetch = (url, options = {}) => {
  const mergedHeaders = {
    'ngrok-skip-browser-warning': 'true',
    ...(options.headers || {}),
  };

  return fetch(url, {
    ...options,
    headers: mergedHeaders,
  });
};

export default {
  API_BASE_URL,
};
