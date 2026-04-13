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

// URL do backend — prioriza variável de ambiente (Vercel/Render), depois fallback local
export const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  'http://localhost:5000';

// Wrapper do fetch que adiciona headers necessários para o ngrok
export const apiFetch = (url, options = {}) => {
  return fetch(url, options);
};

export default {
  API_BASE_URL,
};
