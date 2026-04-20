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

const isBrowser = typeof window !== 'undefined';
const currentHostname = isBrowser ? window.location.hostname : '';
const currentPort = isBrowser ? window.location.port : '';

const isLocalReactDev =
  isBrowser &&
  (currentHostname === 'localhost' || currentHostname === '127.0.0.1') &&
  currentPort === '3000';

const envApiBaseUrl = String(process.env.REACT_APP_API_URL || '').trim();

// URL do backend:
// - se houver REACT_APP_API_URL configurada, ela tem prioridade;
// - no React dev local (localhost:3000), usa o backend em localhost:5000;
// - em acesso público/ngrok/IP local/backend integrado, usa same-origin (/api).
export const API_BASE_URL = envApiBaseUrl || (isLocalReactDev ? 'http://localhost:5000' : '');

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
