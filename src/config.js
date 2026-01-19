/**
 * Configuração da API
 *
 * Para usar com ngrok:
 * 1. Inicie o backend: python backend/api_admissao.py
 * 2. Inicie o ngrok: ngrok http 5000
 * 3. Copie a URL do ngrok e cole aqui em NGROK_API_URL
 * 4. Mude USE_NGROK para true
 */

// URL do ngrok para o backend (atualize quando o ngrok gerar uma nova URL)
const NGROK_API_URL = 'https://automacaolab.ngrok.dev';

// URL local (desenvolvimento)
const LOCAL_API_URL = 'http://localhost:5000';

// Configurar qual URL usar
const USE_NGROK = false; // Mude para false para usar localhost

// URL base da API (selecionada automaticamente)
export const API_BASE_URL = USE_NGROK ? NGROK_API_URL : LOCAL_API_URL;

// Logs para debug
console.log('='.repeat(80));
console.log('🔧 CONFIGURAÇÃO DA API');
console.log('='.repeat(80));
console.log(`📍 Modo: ${USE_NGROK ? 'NGROK (Produção/Remoto)' : 'LOCAL (Desenvolvimento)'}`);
console.log(`🌐 URL da API: ${API_BASE_URL}`);
console.log(`✅ Configuração carregada com sucesso!`);
console.log('='.repeat(80));

export default {
  API_BASE_URL,
  USE_NGROK,
  NGROK_API_URL,
  LOCAL_API_URL
};
