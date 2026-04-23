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

const isLocalHost =
  isBrowser &&
  (currentHostname === 'localhost' || currentHostname === '127.0.0.1');

const isReactDevServer = currentPort === '3000';

const envApiBaseUrl = String(process.env.REACT_APP_API_URL || '').trim();
const envApiIsNgrok = (() => {
  if (!envApiBaseUrl) return false;

  try {
    const hostname = new URL(envApiBaseUrl).hostname;
    return /\.ngrok(-free)?\.app$|\.ngrok\.dev$/i.test(hostname);
  } catch {
    return /\.ngrok(-free)?\.app|\.ngrok\.dev/i.test(envApiBaseUrl);
  }
})();

// Em produção, evitar chamadas diretas browser -> ngrok para não depender de CORS.
// Nestes casos, usa /api para aproveitar rewrite/proxy da própria hospedagem.
const usarProxyMesmoComEnv = isBrowser && !isReactDevServer && envApiIsNgrok;

// URL do backend:
// - REACT_APP_API_URL tem prioridade;
// - em desenvolvimento React (porta 3000), usa o mesmo host na porta 5000;
// - em produção/publicação, usa same-origin (/api) para aproveitar rewrites/proxy.
export const API_BASE_URL = (usarProxyMesmoComEnv ? '' : envApiBaseUrl) || (isReactDevServer
  ? `${isBrowser ? window.location.protocol : 'http:'}//${currentHostname || 'localhost'}:5000`
  : '');

// Wrapper do fetch que adiciona headers necessários para o ngrok
export const apiFetch = (url, options = {}) => {
  const urlString = String(url || '');
  const usarHeaderNgrok = /\.ngrok(-free)?\.app|\.ngrok\.dev/i.test(urlString);
  const mergedHeaders = {
    ...(usarHeaderNgrok ? { 'ngrok-skip-browser-warning': 'true' } : {}),
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
