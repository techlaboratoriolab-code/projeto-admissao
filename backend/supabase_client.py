"""
Cliente Supabase - Gerenciamento de Requisições Processadas
Permite salvar e recuperar requisições já processadas pelo OCR
"""

import os
import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from supabase import create_client, Client
from dotenv import load_dotenv
import json

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURAÇÃO DO CLIENTE SUPABASE
# ============================================

class SupabaseManager:
    """Gerenciador de conexão e operações com Supabase"""

    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.client: Optional[Client] = None

        if self.supabase_url and self.supabase_key:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ Supabase conectado com sucesso!")
            except Exception as e:
                logger.error(f"❌ Erro ao conectar no Supabase: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Credenciais do Supabase não configuradas")

    def is_connected(self) -> bool:
        """Verifica se está conectado ao Supabase"""
        return self.client is not None

    # ============================================
    # SALVAR REQUISIÇÃO PROCESSADA
    # ============================================

    def salvar_requisicao(
        self,
        cod_requisicao: str,
        dados_paciente: Dict[str, Any],
        dados_ocr: Optional[Dict[str, Any]] = None,
        dados_consolidados: Optional[Dict[str, Any]] = None,
        exames: Optional[List[str]] = None,
        exames_ids: Optional[List[int]] = None,
        processado_por: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Salva ou atualiza uma requisição processada no Supabase

        Args:
            cod_requisicao: Código da requisição
            dados_paciente: Dicionário com dados do paciente
            dados_ocr: Dicionário com dados extraídos pelo OCR
            dados_consolidados: Dicionário com dados consolidados finais
            exames: Lista de nomes dos exames
            exames_ids: Lista de IDs dos exames
            processado_por: Nome/ID de quem processou

        Returns:
            Dicionário com sucesso e dados salvos ou erro
        """
        if not self.is_connected():
            return {
                "sucesso": 0,
                "erro": "Supabase não está conectado"
            }

        try:
            logger.info(f"[SUPABASE] Salvando requisição: {cod_requisicao}")

            # ============================================
            # EXTRAIR DADOS DO PACIENTE
            # ============================================
            nome_paciente = dados_paciente.get('name') or dados_paciente.get('nome') or dados_paciente.get('NomPaciente')
            cpf_paciente = dados_paciente.get('cpf') or dados_paciente.get('NumCPF') or dados_paciente.get('CPF')

            # Limpar CPF (apenas números)
            if cpf_paciente:
                cpf_paciente = ''.join(filter(str.isdigit, str(cpf_paciente)))[:11]

            # Data de nascimento
            data_nasc = dados_paciente.get('birthDate') or dados_paciente.get('dtaNasc') or dados_paciente.get('DtaNasc') or dados_paciente.get('DtaNascimento')
            if data_nasc and isinstance(data_nasc, str):
                try:
                    # Converter para formato de data
                    if 'T' in data_nasc:
                        data_nasc = data_nasc.split('T')[0]
                    # Tentar diversos formatos
                    if ',' in data_nasc:  # Formato: "Tue, 22 Feb 1977 00:00:00 GMT"
                        from dateutil import parser
                        data_nasc = parser.parse(data_nasc).date()
                    else:
                        data_nasc = datetime.strptime(data_nasc, '%Y-%m-%d').date()
                except:
                    data_nasc = None

            # ID do paciente
            id_paciente = dados_paciente.get('idPaciente')
            
            # ============================================
            # EXTRAIR DADOS DOS CONSOLIDADOS (ANINHADOS)
            # ============================================
            if dados_consolidados:
                # Os dados estão dentro de requisicoes[0] no consolidado
                requisicao_consolidada = None
                if 'requisicoes' in dados_consolidados and len(dados_consolidados['requisicoes']) > 0:
                    requisicao_consolidada = dados_consolidados['requisicoes'][0]
                else:
                    requisicao_consolidada = dados_consolidados

                # Convênio (tentar vários caminhos)
                id_convenio = dados_consolidados.get('idConvenio')
                nome_convenio = dados_consolidados.get('nomeConvenio')
                matricula_convenio = dados_consolidados.get('matriculaConvenio')

                if requisicao_consolidada:
                    # Tentar extrair de convenio aninhado
                    convenio_obj = requisicao_consolidada.get('convenio', {})
                    if not id_convenio:
                        id_convenio_val = convenio_obj.get('id') or convenio_obj.get('idConvenio')
                        if isinstance(id_convenio_val, dict):
                            id_convenio = id_convenio_val.get('valor')
                        else:
                            id_convenio = id_convenio_val
                    if not nome_convenio:
                        nome_val = convenio_obj.get('nome', {})
                        if isinstance(nome_val, dict):
                            nome_convenio = nome_val.get('valor')
                        else:
                            nome_convenio = nome_val
                    if not matricula_convenio:
                        mat_val = convenio_obj.get('matConvenio', {})
                        if isinstance(mat_val, dict):
                            matricula_convenio = mat_val.get('valor')
                        else:
                            matricula_convenio = mat_val

                    # Médico
                    medico_obj = requisicao_consolidada.get('medico', {})
                    id_medico_val = medico_obj.get('id') or medico_obj.get('idMedico') or dados_consolidados.get('idMedico')
                    if isinstance(id_medico_val, dict):
                        id_medico = id_medico_val.get('valor')
                    else:
                        id_medico = id_medico_val

                    nome_medico_val = medico_obj.get('NomMedico', {})
                    if isinstance(nome_medico_val, dict):
                        nome_medico = nome_medico_val.get('valor')
                    else:
                        nome_medico = nome_medico_val or dados_consolidados.get('nomeMedico')

                    # Data de coleta
                    requisicao_obj = requisicao_consolidada.get('requisicao', {})
                    data_coleta_val = requisicao_obj.get('dtaColeta', {})
                    if isinstance(data_coleta_val, dict):
                        data_coleta = data_coleta_val.get('valor')
                    else:
                        data_coleta = data_coleta_val or dados_consolidados.get('dtaColeta')

                    # Extrair dados ADICIONAIS do paciente dos consolidados
                    paciente_obj = requisicao_consolidada.get('paciente', {})

                    # ID do paciente (se não foi encontrado antes)
                    if not id_paciente:
                        id_pac_val = paciente_obj.get('id') or paciente_obj.get('idPaciente')
                        if isinstance(id_pac_val, dict):
                            id_paciente = id_pac_val.get('valor')
                        else:
                            id_paciente = id_pac_val

                    # Data de nascimento (se não foi encontrada antes)
                    if not data_nasc:
                        dta_nasc_val = paciente_obj.get('DtaNascimento') or paciente_obj.get('dtaNascimento')
                        if isinstance(dta_nasc_val, dict):
                            dta_nasc_str = dta_nasc_val.get('valor')
                        else:
                            dta_nasc_str = dta_nasc_val

                        if dta_nasc_str and isinstance(dta_nasc_str, str):
                            try:
                                # Converter formato GMT: "Tue, 22 Feb 1977 00:00:00 GMT"
                                if ',' in dta_nasc_str:
                                    from dateutil import parser
                                    data_nasc = parser.parse(dta_nasc_str).date()
                                elif 'T' in dta_nasc_str:
                                    data_nasc = datetime.strptime(dta_nasc_str.split('T')[0], '%Y-%m-%d').date()
                                else:
                                    data_nasc = datetime.strptime(dta_nasc_str, '%Y-%m-%d').date()
                            except:
                                pass

                    # Matrícula do convênio do paciente (MatConvenio)
                    if not matricula_convenio:
                        mat_conv_val = paciente_obj.get('MatConvenio') or paciente_obj.get('matriculaConvenio')
                        if isinstance(mat_conv_val, dict):
                            matricula_convenio = mat_conv_val.get('valor')
                        else:
                            matricula_convenio = mat_conv_val

                    # CPF (atualizar se vier dos consolidados)
                    if not cpf_paciente:
                        cpf_val = paciente_obj.get('cpf') or paciente_obj.get('CPF')
                        if isinstance(cpf_val, dict):
                            cpf_paciente = cpf_val.get('valor')
                        else:
                            cpf_paciente = cpf_val
                        if cpf_paciente:
                            cpf_paciente = ''.join(filter(str.isdigit, str(cpf_paciente)))[:11]

                    # Nome do paciente (atualizar se vier dos consolidados)
                    if not nome_paciente:
                        nome_pac_val = paciente_obj.get('NomPaciente') or paciente_obj.get('nomePaciente')
                        if isinstance(nome_pac_val, dict):
                            nome_paciente = nome_pac_val.get('valor')
                        else:
                            nome_paciente = nome_pac_val
                else:
                    id_convenio = dados_consolidados.get('idConvenio')
                    nome_convenio = dados_consolidados.get('nomeConvenio')
                    matricula_convenio = dados_consolidados.get('matriculaConvenio')
                    id_medico = dados_consolidados.get('idMedico')
                    nome_medico = dados_consolidados.get('nomeMedico')
                    data_coleta = dados_consolidados.get('dtaColeta')
            else:
                id_convenio = None
                nome_convenio = None
                matricula_convenio = None
                id_medico = None
                nome_medico = None
                data_coleta = None

            # Fallback para matricula_convenio de dados_paciente
            if not matricula_convenio:
                matricula_convenio = dados_paciente.get('insuranceCardNumber') or dados_paciente.get('matriculaConvenio') or dados_paciente.get('MatConvenio')

            # Converter data de coleta
            if data_coleta and isinstance(data_coleta, str):
                try:
                    # Formatos possíveis: DD/MM/YYYY, YYYY-MM-DD, ou com T
                    if 'T' in data_coleta:
                        data_coleta = data_coleta.split('T')[0]

                    # Tentar DD/MM/YYYY primeiro
                    if '/' in data_coleta:
                        data_coleta = datetime.strptime(data_coleta, '%d/%m/%Y').date()
                    else:
                        data_coleta = datetime.strptime(data_coleta, '%Y-%m-%d').date()
                except Exception as e:
                    logger.warning(f"Erro ao converter data de coleta '{data_coleta}': {e}")
                    data_coleta = None

            # ============================================
            # EXTRAIR CONTADORES DE IMAGENS DO OCR
            # ============================================
            total_imagens = 0
            imagens_processadas = 0

            if dados_ocr:
                # Tentar vários caminhos possíveis
                total_imagens = dados_ocr.get('total_imagens', 0)
                imagens_processadas = dados_ocr.get('imagens_processadas', 0)

                # Se não encontrou, contar do array de resultados
                if total_imagens == 0 and 'resultados' in dados_ocr:
                    resultados = dados_ocr.get('resultados', [])
                    if isinstance(resultados, list):
                        total_imagens = len(resultados)
                        imagens_processadas = len(resultados)

            # ============================================
            # EXTRAIR STATUS APLIS (StatusExame)
            # 0 = Em andamento, 1 = Concluído, 2 = Cancelado
            # ============================================
            status_aplis = None
            status_aplis_descricao = None

            if dados_consolidados:
                # Tentar extrair do nível superior
                status_aplis = dados_consolidados.get('StatusExame')

                # Se não encontrou, tentar dentro de requisicoes[0]
                if status_aplis is None and requisicao_consolidada:
                    status_aplis = requisicao_consolidada.get('StatusExame')

                # Converter para inteiro se for string
                if status_aplis is not None:
                    try:
                        status_aplis = int(status_aplis)
                        # Mapear descrição
                        if status_aplis == 0:
                            status_aplis_descricao = 'Em andamento'
                        elif status_aplis == 1:
                            status_aplis_descricao = 'Concluído'
                        elif status_aplis == 2:
                            status_aplis_descricao = 'Cancelado'
                    except (ValueError, TypeError):
                        status_aplis = None

            # ============================================
            # EXTRAIR IDS DE EXAMES (DEDUPLICAR)
            # ============================================
            exames_ids_unicos = []
            if exames_ids:
                # Converter para inteiros e remover duplicatas mantendo ordem
                ids_vistos = set()
                for id_exame in exames_ids:
                    try:
                        id_int = int(id_exame) if isinstance(id_exame, str) else id_exame
                        if id_int not in ids_vistos:
                            ids_vistos.add(id_int)
                            exames_ids_unicos.append(id_int)
                    except (ValueError, TypeError):
                        continue

            # Montar objeto para salvar
            dados = {
                "cod_requisicao": cod_requisicao,
                "dados_paciente": dados_paciente,
                "dados_ocr": dados_ocr or {},
                "dados_consolidados": dados_consolidados or {},
                "id_paciente": id_paciente,
                "nome_paciente": nome_paciente,
                "cpf_paciente": cpf_paciente,
                "data_nascimento": data_nasc.isoformat() if data_nasc else None,
                "id_convenio": id_convenio,
                "nome_convenio": nome_convenio,
                "matricula_convenio": matricula_convenio,
                "id_medico": id_medico,
                "nome_medico": nome_medico,
                "exames": exames or [],
                "exames_ids": exames_ids_unicos,
                "data_coleta": data_coleta.isoformat() if data_coleta else None,
                "status": "processado",
                "status_aplis": status_aplis,
                "status_aplis_descricao": status_aplis_descricao,
                "processado_por": processado_por,
                "total_imagens": total_imagens,
                "imagens_processadas": imagens_processadas
            }

            # Verificar se já existe
            result = self.client.table('requisicoes_processadas') \
                .select('id') \
                .eq('cod_requisicao', cod_requisicao) \
                .execute()

            if result.data and len(result.data) > 0:
                # Atualizar existente
                logger.info(f"[SUPABASE] Atualizando requisição existente: {cod_requisicao}")
                update_result = self.client.table('requisicoes_processadas') \
                    .update(dados) \
                    .eq('cod_requisicao', cod_requisicao) \
                    .execute()

                return {
                    "sucesso": 1,
                    "mensagem": "Requisição atualizada com sucesso",
                    "dados": update_result.data[0] if update_result.data else None,
                    "acao": "update"
                }
            else:
                # Inserir nova
                logger.info(f"[SUPABASE] Inserindo nova requisição: {cod_requisicao}")
                insert_result = self.client.table('requisicoes_processadas') \
                    .insert(dados) \
                    .execute()

                return {
                    "sucesso": 1,
                    "mensagem": "Requisição salva com sucesso",
                    "dados": insert_result.data[0] if insert_result.data else None,
                    "acao": "insert"
                }

        except Exception as e:
            logger.error(f"[SUPABASE] Erro ao salvar requisição: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "sucesso": 0,
                "erro": str(e)
            }

    # ============================================
    # BUSCAR REQUISIÇÕES
    # ============================================

    def buscar_requisicao(self, cod_requisicao: str) -> Dict[str, Any]:
        """
        Busca uma requisição específica pelo código

        Args:
            cod_requisicao: Código da requisição

        Returns:
            Dicionário com sucesso e dados ou erro
        """
        if not self.is_connected():
            return {"sucesso": 0, "erro": "Supabase não conectado"}

        try:
            logger.info(f"[SUPABASE] Buscando requisição: {cod_requisicao}")

            result = self.client.table('requisicoes_processadas') \
                .select('*') \
                .eq('cod_requisicao', cod_requisicao) \
                .execute()

            if result.data and len(result.data) > 0:
                return {
                    "sucesso": 1,
                    "dados": result.data[0]
                }
            else:
                return {
                    "sucesso": 0,
                    "erro": "Requisição não encontrada"
                }

        except Exception as e:
            logger.error(f"[SUPABASE] Erro ao buscar requisição: {e}")
            return {"sucesso": 0, "erro": str(e)}

    def listar_requisicoes_recentes(self, limite: int = 50) -> Dict[str, Any]:
        """
        Lista as requisições mais recentes

        Args:
            limite: Número máximo de requisições

        Returns:
            Dicionário com sucesso e lista de requisições ou erro
        """
        if not self.is_connected():
            return {"sucesso": 0, "erro": "Supabase não conectado"}

        try:
            logger.info(f"[SUPABASE] Listando {limite} requisições recentes")

            result = self.client.table('requisicoes_processadas') \
                .select('id, cod_requisicao, nome_paciente, cpf_paciente, data_nascimento, data_coleta, created_at, status, exames, dados_paciente') \
                .order('created_at', desc=True) \
                .limit(limite) \
                .execute()

            return {
                "sucesso": 1,
                "total": len(result.data),
                "requisicoes": result.data
            }

        except Exception as e:
            logger.error(f"[SUPABASE] Erro ao listar requisições: {e}")
            return {"sucesso": 0, "erro": str(e)}

    def buscar_por_cpf(self, cpf: str) -> Dict[str, Any]:
        """
        Busca requisições por CPF do paciente

        Args:
            cpf: CPF do paciente (apenas números)

        Returns:
            Dicionário com sucesso e lista de requisições ou erro
        """
        if not self.is_connected():
            return {"sucesso": 0, "erro": "Supabase não conectado"}

        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))[:11]

            logger.info(f"[SUPABASE] Buscando requisições por CPF: {cpf_limpo}")

            result = self.client.table('requisicoes_processadas') \
                .select('*') \
                .eq('cpf_paciente', cpf_limpo) \
                .order('created_at', desc=True) \
                .execute()

            return {
                "sucesso": 1,
                "total": len(result.data),
                "requisicoes": result.data
            }

        except Exception as e:
            logger.error(f"[SUPABASE] Erro ao buscar por CPF: {e}")
            return {"sucesso": 0, "erro": str(e)}


# ============================================
# INSTÂNCIA GLOBAL
# ============================================

# Criar instância global do gerenciador
supabase_manager = SupabaseManager()
