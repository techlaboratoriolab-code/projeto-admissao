# -*- coding: utf-8 -*-
"""
Processamento automatico agendado (4h da manha)
Busca requisicoes disponiveis, processa OCR de todas as imagens,
e salva resultados no Supabase para revisao pelos usuarios.
"""

import logging
import time
import uuid
import json
import traceback
import os
import threading
import re
import requests as http_requests
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Usar o logger root ou api_admissao para que os logs apareçam no mesmo arquivo
logger = logging.getLogger('api_admissao')

SYSTEM_USER_ID = "sistema-automatico"
SYSTEM_USER_NAME = "Sistema Automatico (4h)"

# URL base do proprio Flask (chamadas internas)
FLASK_BASE_URL = "http://localhost:5000"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULER_LOGS_DIR = os.path.join(BASE_DIR, "logs", "scheduler_execucoes")
SCHEDULER_SUMMARY_LOG = os.path.join(BASE_DIR, "logs", "scheduler_execucoes.log")

# Lock global para evitar execucao dupla (APScheduler interno + disparar_4h.ps1)
_job_lock = threading.Lock()
_job_running = False


def _garantir_diretorios_logs_scheduler():
    os.makedirs(SCHEDULER_LOGS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(SCHEDULER_SUMMARY_LOG), exist_ok=True)


def _novo_contexto_execucao(origem_disparo):
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
    return {
        "run_id": run_id,
        "origem_disparo": origem_disparo,
        "inicio": datetime.now().isoformat(),
        "fim": None,
        "duracao_segundos": None,
        "status": "em_andamento",
        "sessao_id": None,
        "metricas": {
            "total_itens": 0,
            "itens_processados": 0,
            "itens_com_erro": 0,
            "itens_com_sucesso": 0,
        },
        "eventos": [],
        "erros": [],
    }


def _registrar_evento_execucao(ctx, etapa, mensagem, nivel="info", extra=None):
    evento = {
        "timestamp": datetime.now().isoformat(),
        "etapa": etapa,
        "nivel": nivel.upper(),
        "mensagem": mensagem,
    }
    if extra is not None:
        evento["extra"] = extra
    ctx["eventos"].append(evento)

    prefixo = f"[SCHEDULER][RUN={ctx['run_id']}][{etapa}] {mensagem}"
    if nivel == "error":
        logger.error(prefixo)
    elif nivel == "warning":
        logger.warning(prefixo)
    else:
        logger.info(prefixo)


def _registrar_erro_execucao(ctx, etapa, mensagem, exc=None, extra=None):
    erro = {
        "timestamp": datetime.now().isoformat(),
        "etapa": etapa,
        "mensagem": mensagem,
        "extra": extra or {},
    }
    if exc is not None:
        erro["exception"] = str(exc)
        erro["traceback"] = traceback.format_exc()
    ctx["erros"].append(erro)
    _registrar_evento_execucao(ctx, etapa, mensagem, nivel="error", extra=erro.get("extra"))


def _finalizar_contexto_execucao(ctx, status, motivo=None):
    fim = datetime.now()
    inicio = datetime.fromisoformat(ctx["inicio"])
    duracao = (fim - inicio).total_seconds()
    ctx["fim"] = fim.isoformat()
    ctx["duracao_segundos"] = round(duracao, 2)
    ctx["status"] = status
    if motivo:
        ctx["motivo_finalizacao"] = motivo


def _persistir_relatorio_execucao(ctx):
    _garantir_diretorios_logs_scheduler()

    arquivo_relatorio = os.path.join(SCHEDULER_LOGS_DIR, f"run_{ctx['run_id']}.json")
    with open(arquivo_relatorio, "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)

    resumo = {
        "run_id": ctx["run_id"],
        "inicio": ctx.get("inicio"),
        "fim": ctx.get("fim"),
        "status": ctx.get("status"),
        "origem_disparo": ctx.get("origem_disparo"),
        "sessao_id": ctx.get("sessao_id"),
        "duracao_segundos": ctx.get("duracao_segundos"),
        "total_itens": ctx.get("metricas", {}).get("total_itens", 0),
        "itens_com_sucesso": ctx.get("metricas", {}).get("itens_com_sucesso", 0),
        "itens_com_erro": ctx.get("metricas", {}).get("itens_com_erro", 0),
        "qtd_eventos": len(ctx.get("eventos", [])),
        "qtd_erros": len(ctx.get("erros", [])),
        "arquivo_relatorio": arquivo_relatorio,
    }

    with open(SCHEDULER_SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(resumo, ensure_ascii=False) + "\n")

    logger.info("[SCHEDULER] Relatorio salvo em %s", arquivo_relatorio)
    logger.info("[SCHEDULER] Resumo append em %s", SCHEDULER_SUMMARY_LOG)


def _normalizar_codigo_requisicao(codigo):
    digitos = re.sub(r"\D", "", str(codigo or "").strip())
    if not digitos:
        return ""
    if len(digitos) < 13:
        digitos = digitos.zfill(13)
    elif len(digitos) > 13:
        digitos = digitos[-13:]
    return digitos


def _buscar_requisicoes_disponiveis(limite=15, max_tentativas=4):
    """
    Busca requisicoes disponiveis com retry e fallback de janela de datas.
    Mitiga falhas transientes do apLIS (ex.: 403/timeout na madrugada).
    """
    hoje = datetime.now()
    ontem = (hoje - timedelta(days=1)).strftime("%Y-%m-%d")
    dois_dias = (hoje - timedelta(days=2)).strftime("%Y-%m-%d")
    tres_dias = (hoje - timedelta(days=3)).strftime("%Y-%m-%d")

    payloads = [
        {"filtrarAguardaAdmissao": True, "limite": limite},
        {
            "filtrarAguardaAdmissao": True,
            "limite": limite,
            "periodoIni": ontem,
            "periodoFim": ontem,
        },
        {
            "filtrarAguardaAdmissao": True,
            "limite": limite,
            "periodoIni": dois_dias,
            "periodoFim": ontem,
        },
        {
            "filtrarAguardaAdmissao": True,
            "limite": limite,
            "periodoIni": tres_dias,
            "periodoFim": ontem,
        },
    ]

    ultimo_erro = "falha desconhecida"

    for tentativa in range(1, max_tentativas + 1):
        for idx, payload in enumerate(payloads, start=1):
            try:
                logger.info(
                    "[SCHEDULER] Tentativa %d/%d para listar requisicoes (perfil %d/%d)",
                    tentativa,
                    max_tentativas,
                    idx,
                    len(payloads),
                )

                resp = http_requests.post(
                    f"{FLASK_BASE_URL}/api/requisicoes/disponiveis",
                    json=payload,
                    timeout=60,
                )

                if resp.status_code != 200:
                    ultimo_erro = f"HTTP {resp.status_code} - {resp.text[:300]}"
                    logger.warning(
                        "[SCHEDULER] Falha ao listar requisicoes (tentativa %d, perfil %d): %s",
                        tentativa,
                        idx,
                        ultimo_erro,
                    )
                    continue

                data = resp.json()
                if not data.get("sucesso"):
                    detalhe = data.get("detalhe") or data.get("erro") or "desconhecido"
                    ultimo_erro = str(detalhe)
                    logger.warning(
                        "[SCHEDULER] API /disponiveis retornou sucesso=0 (tentativa %d, perfil %d): %s",
                        tentativa,
                        idx,
                        detalhe,
                    )
                    continue

                requisicoes = data.get("requisicoes", [])
                logger.info(
                    "[SCHEDULER] %d requisicoes encontradas (tentativa %d, perfil %d)",
                    len(requisicoes),
                    tentativa,
                    idx,
                )
                return requisicoes

            except Exception as e:
                ultimo_erro = str(e)
                logger.warning(
                    "[SCHEDULER] Excecao ao listar requisicoes (tentativa %d, perfil %d): %s",
                    tentativa,
                    idx,
                    e,
                )

        if tentativa < max_tentativas:
            espera = 20 * tentativa
            logger.info(
                "[SCHEDULER] Aguardando %ds antes de nova tentativa de listagem...",
                espera,
            )
            time.sleep(espera)

    raise Exception(f"Falha ao buscar requisicoes disponiveis apos retries: {ultimo_erro}")


def executar_processamento_automatico(origem_disparo="agendado"):
    """
    Entry point chamado pelo APScheduler as 4h.
    Replica o fluxo do frontend processarTodasRequisicoes:
      1. Buscar requisicoes disponiveis
      2. Criar sessao no Supabase
      3. Para cada: buscar dados + imagens, OCR, consolidar, salvar snapshot
      4. Marcar sessao como 'revisao'
    """
    global _job_running
    # Evitar dupla execucao (APScheduler interno + disparar_4h.ps1 simultâneos)
    if not _job_lock.acquire(blocking=False):
        logger.warning("[SCHEDULER] Job ja em execucao. Ignorando disparo duplicado.")
        return
    _job_running = True
    try:
        _executar_processamento_interno(origem_disparo=origem_disparo)
    finally:
        _job_running = False
        _job_lock.release()


def _executar_processamento_interno(origem_disparo="agendado"):
    """Logica real do processamento, chamada com lock adquirido."""
    ctx = _novo_contexto_execucao(origem_disparo)
    logger.info("=" * 80)
    logger.info("[SCHEDULER] INICIO PROCESSAMENTO AUTOMATICO - %s", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 80)
    _registrar_evento_execucao(ctx, "inicio", "Processamento automatico iniciado", extra={"origem_disparo": origem_disparo})

    # Fim de semana nao processa - requisicoes de sexta sao processadas na segunda
    dia_semana = datetime.now().weekday()
    if dia_semana in (5, 6):  # Sabado=5, Domingo=6
        logger.info("[SCHEDULER] Fim de semana - pulando processamento. Requisicoes serao processadas na segunda-feira.")
        _registrar_evento_execucao(ctx, "regra_negocio", "Execucao pulada por fim de semana", extra={"dia_semana": dia_semana})
        _finalizar_contexto_execucao(ctx, "pulado", motivo="fim_de_semana")
        _persistir_relatorio_execucao(ctx)
        return

    try:
        from supabase_client import supabase_manager
    except Exception as e:
        logger.error("[SCHEDULER] Erro ao importar supabase_client: %s", e)
        _registrar_erro_execucao(ctx, "bootstrap", "Erro ao importar supabase_client", exc=e)
        _finalizar_contexto_execucao(ctx, "erro", motivo="import_supabase")
        _persistir_relatorio_execucao(ctx)
        return

    if not supabase_manager or not supabase_manager.is_connected():
        logger.error("[SCHEDULER] Supabase nao conectado. Abortando.")
        _registrar_evento_execucao(ctx, "bootstrap", "Supabase nao conectado; execucao abortada", nivel="error")
        _finalizar_contexto_execucao(ctx, "erro", motivo="supabase_desconectado")
        _persistir_relatorio_execucao(ctx)
        return

    sb = supabase_manager.client

    try:
        # Verificar se ja existe sessao ativa DO DIA DE HOJE
        # Sessoes de dias anteriores nao bloqueiam a execucao
        result = sb.table('fila_sessao').select('id, iniciado_por_nome, created_at, status').in_('status', ['processando', 'revisao']).execute()
        if result.data and len(result.data) > 0:
            hoje = datetime.now().strftime('%Y-%m-%d')
            sessao_bloqueante = None
            for sessao in result.data:
                created = sessao.get('created_at', '')
                # created_at vem no formato ISO (ex: 2026-02-26T04:00:12.123456+00:00)
                data_sessao = str(created).split('T')[0] if created else ''
                if data_sessao == hoje:
                    sessao_bloqueante = sessao
                    break
                else:
                    # Sessao de dia anterior em 'processando' -> marcar como encerrada
                    if sessao.get('status') == 'processando':
                        logger.warning("[SCHEDULER] Sessao antiga %s (de %s) estava em 'processando'. Marcando como 'revisao'.",
                                       sessao['id'], data_sessao)
                        _atualizar_sessao(sb, sessao['id'], {'status': 'revisao'})

            if sessao_bloqueante:
                logger.warning("[SCHEDULER] Sessao ativa de HOJE encontrada (id=%s, por=%s). Abortando.",
                               sessao_bloqueante['id'], sessao_bloqueante.get('iniciado_por_nome'))
                _registrar_evento_execucao(
                    ctx,
                    "validacao_sessao",
                    "Execucao abortada por sessao ativa de hoje",
                    nivel="warning",
                    extra={"sessao_bloqueante_id": sessao_bloqueante['id']},
                )
                _finalizar_contexto_execucao(ctx, "pulado", motivo="sessao_ativa_hoje")
                _persistir_relatorio_execucao(ctx)
                return
            else:
                logger.info("[SCHEDULER] Sessoes ativas encontradas sao de dias anteriores. Prosseguindo.")
                _registrar_evento_execucao(ctx, "validacao_sessao", "Sessoes antigas detectadas, execucao autorizada")

        # =============================================
        # ETAPA 1: Buscar requisicoes disponiveis
        # =============================================
        logger.info("[SCHEDULER] Etapa 1: Buscando requisicoes disponiveis...")

        requisicoes = _buscar_requisicoes_disponiveis(limite=15, max_tentativas=4)
        _registrar_evento_execucao(ctx, "etapa_1", "Busca de requisicoes concluida", extra={"qtd_requisicoes": len(requisicoes)})

        if not requisicoes:
            logger.info("[SCHEDULER] Nenhuma requisicao pendente. Finalizando.")
            _finalizar_contexto_execucao(ctx, "sem_itens", motivo="nenhuma_requisicao_pendente")
            _persistir_relatorio_execucao(ctx)
            return

        # =============================================
        # DEDUPLICAR pares 0085/0200
        # Se 0085XXX e 0200XXX existem para o mesmo paciente/data,
        # processar apenas UM (preferir 0085). O endpoint /api/requisicao/{cod}
        # ja sincroniza os dados do par correspondente automaticamente.
        # =============================================

        # Primeiro ordena: 0085 antes de 0200 para preferir 0085 quando ambos presentes
        def _ordem_preferencia(req):
            cod = _normalizar_codigo_requisicao(req.get('CodRequisicao') or req.get('codRequisicao') or req.get('codigo') or req.get('cod', ''))
            if len(cod) >= 4 and cod[:4] == '0085':
                return 0  # 0085 tem prioridade
            if len(cod) >= 4 and cod[:4] == '0200':
                return 1  # 0200 e descartado se 0085 existir
            return 2

        requisicoes_ordenadas = sorted(requisicoes, key=_ordem_preferencia)

        requisicoes_dedup = []
        codigos_adicionados = set()
        for req in requisicoes_ordenadas:
            cod = _normalizar_codigo_requisicao(req.get('CodRequisicao') or req.get('codRequisicao') or req.get('codigo') or req.get('cod', ''))
            # Calcular codigo do par correspondente
            cod_par = None
            if len(cod) >= 4:
                if cod[:4] == '0085':
                    cod_par = '0200' + cod[4:]
                elif cod[:4] == '0200':
                    cod_par = '0085' + cod[4:]
            # Se o par ja foi adicionado, pular este
            if cod_par and cod_par in codigos_adicionados:
                logger.info("[SCHEDULER] Dedup: pulando %s (par %s ja na fila)", cod, cod_par)
                continue
            codigos_adicionados.add(cod)
            requisicoes_dedup.append(req)

        if len(requisicoes_dedup) < len(requisicoes):
            logger.info("[SCHEDULER] Dedup 0085/0200: %d -> %d requisicoes (removidos %d pares duplicados)",
                        len(requisicoes), len(requisicoes_dedup), len(requisicoes) - len(requisicoes_dedup))
        requisicoes = requisicoes_dedup
        ctx["metricas"]["total_itens"] = len(requisicoes)

        # =============================================
        # ETAPA 2: Criar sessao no Supabase
        # =============================================
        sessao_id = str(uuid.uuid4())
        ctx["sessao_id"] = sessao_id
        logger.info("[SCHEDULER] Etapa 2: Criando sessao %s com %d itens", sessao_id, len(requisicoes))
        _registrar_evento_execucao(ctx, "etapa_2", "Sessao criada para processamento", extra={"sessao_id": sessao_id, "total_itens": len(requisicoes)})

        sb.table('fila_sessao').insert({
            'id': sessao_id,
            'status': 'processando',
            'total_itens': len(requisicoes),
            'itens_processados': 0,
            'iniciado_por': SYSTEM_USER_ID,
            'iniciado_por_nome': SYSTEM_USER_NAME,
        }).execute()

        # =============================================
        # ETAPA 3: Inserir items na fila
        # =============================================
        itens_para_inserir = []
        for idx, req in enumerate(requisicoes):
            cod = _normalizar_codigo_requisicao(req.get('CodRequisicao') or req.get('codRequisicao') or req.get('codigo') or req.get('cod', ''))
            itens_para_inserir.append({
                'sessao_id': sessao_id,
                'cod_requisicao': str(cod),
                'paciente_nome': req.get('NomPaciente') or req.get('paciente') or None,
                'cpf': req.get('NumCPF') or req.get('cpf') or None,
                'status': 'pendente',
                'processado_por': SYSTEM_USER_ID,
                'ordem': idx,
            })

        result_insert = sb.table('fila_admissao').insert(itens_para_inserir).execute()
        itens_inseridos = result_insert.data or []
        logger.info("[SCHEDULER] %d itens inseridos na fila", len(itens_inseridos))
        _registrar_evento_execucao(ctx, "etapa_3", "Itens inseridos na fila", extra={"itens_inseridos": len(itens_inseridos)})

        if not itens_inseridos:
            logger.error("[SCHEDULER] Falha ao inserir itens no Supabase")
            sb.table('fila_sessao').update({'status': 'cancelado'}).eq('id', sessao_id).execute()
            _registrar_evento_execucao(ctx, "etapa_3", "Nenhum item inserido; sessao cancelada", nivel="error", extra={"sessao_id": sessao_id})
            _finalizar_contexto_execucao(ctx, "erro", motivo="falha_insercao_itens")
            _persistir_relatorio_execucao(ctx)
            return

        # =============================================
        # ETAPA 4: Processar cada item
        # =============================================
        total = len(itens_inseridos)
        processados = 0
        erros = 0

        for i, item in enumerate(itens_inseridos):
            item_id = item['id']
            cod = _normalizar_codigo_requisicao(item.get('cod_requisicao'))

            if not cod:
                raise Exception(f"Código de requisição inválido no item da fila: {item.get('cod_requisicao')}")

            logger.info("[SCHEDULER] [%d/%d] Processando requisicao %s...", i + 1, total, cod)
            _registrar_evento_execucao(ctx, "etapa_4", "Inicio de processamento de item", extra={"indice": i + 1, "total": total, "cod_requisicao": cod, "item_id": item_id})

            try:
                # Marcar como processando
                _atualizar_item(sb, item_id, {'status': 'processando'})
                _atualizar_sessao(sb, sessao_id, {'itens_processados': i})

                # 4a. Buscar dados da requisicao
                logger.info("[SCHEDULER] [%d/%d] Buscando dados de %s...", i + 1, total, cod)
                resp_req = http_requests.get(f"{FLASK_BASE_URL}/api/requisicao/{cod}", timeout=120)

                if resp_req.status_code != 200:
                    raise Exception(f"Erro ao buscar requisicao: HTTP {resp_req.status_code}")

                dados_req = resp_req.json()
                if not dados_req.get('sucesso'):
                    raise Exception(f"API erro: {dados_req.get('erro', 'desconhecido')}")

                # Extrair dados da API
                dados_api = dados_req
                imagens = dados_req.get('imagens', [])

                logger.info("[SCHEDULER] [%d/%d] %d imagens encontradas para %s",
                            i + 1, total, len(imagens), cod)

                # 4b. Processar OCR de cada imagem
                resultados_ocr = []
                for img_idx, img in enumerate(imagens):
                    logger.info("[SCHEDULER] [%d/%d] OCR imagem %d/%d: %s",
                                i + 1, total, img_idx + 1, len(imagens), img.get('nome', ''))

                    try:
                        ocr_result = _processar_ocr_imagem(img)
                        if ocr_result:
                            resultados_ocr.append(ocr_result)
                    except Exception as ocr_err:
                        logger.error("[SCHEDULER] Erro OCR imagem %s: %s", img.get('nome', ''), ocr_err)

                    # Delay entre imagens (respeitar rate limit)
                    if img_idx < len(imagens) - 1:
                        time.sleep(10)

                logger.info("[SCHEDULER] [%d/%d] %d/%d imagens processadas com OCR",
                            i + 1, total, len(resultados_ocr), len(imagens))

                # 4c. Consolidar resultados
                resultado_consolidado = None
                if resultados_ocr:
                    resultado_consolidado = _consolidar_resultados(resultados_ocr, cod, dados_api)

                # 4d. Construir snapshots
                form_data_snapshot = _construir_form_data(dados_api, resultado_consolidado)
                patient_data_snapshot = _construir_patient_data(dados_api, resultado_consolidado)

                # Buscar exames se houver resultado consolidado
                if resultado_consolidado:
                    _enriquecer_form_com_exames(form_data_snapshot, resultado_consolidado)

                # 4e. Salvar no Supabase
                _atualizar_item(sb, item_id, {
                    'status': 'processado',
                    'form_data_snapshot': form_data_snapshot,
                    'patient_data_snapshot': patient_data_snapshot,
                    'resultado_consolidado': resultado_consolidado,
                    'paciente_nome': patient_data_snapshot.get('name') if patient_data_snapshot else None,
                    'cpf': patient_data_snapshot.get('cpf') if patient_data_snapshot else None,
                })

                processados += 1
                ctx["metricas"]["itens_com_sucesso"] = processados
                ctx["metricas"]["itens_processados"] = i + 1
                logger.info("[SCHEDULER] [%d/%d] %s processado com sucesso!", i + 1, total, cod)
                _registrar_evento_execucao(ctx, "etapa_4", "Item processado com sucesso", extra={"indice": i + 1, "total": total, "cod_requisicao": cod, "qtd_imagens": len(imagens), "qtd_ocr_ok": len(resultados_ocr)})

            except Exception as e:
                erros += 1
                ctx["metricas"]["itens_com_erro"] = erros
                ctx["metricas"]["itens_processados"] = i + 1
                logger.error("[SCHEDULER] [%d/%d] ERRO em %s: %s", i + 1, total, cod, e)
                logger.error(traceback.format_exc())
                _registrar_erro_execucao(
                    ctx,
                    "etapa_4",
                    "Erro ao processar item",
                    exc=e,
                    extra={"indice": i + 1, "total": total, "cod_requisicao": cod, "item_id": item_id},
                )
                _atualizar_item(sb, item_id, {
                    'status': 'erro',
                    'erro': str(e)[:500]
                })

            # Delay entre requisicoes
            if i < total - 1:
                logger.info("[SCHEDULER] Aguardando 5s antes da proxima requisicao...")
                time.sleep(5)

        # =============================================
        # ETAPA 5: Marcar sessao como revisao
        # =============================================
        _atualizar_sessao(sb, sessao_id, {
            'status': 'revisao',
            'itens_processados': total,
        })

        logger.info("=" * 80)
        logger.info("[SCHEDULER] CONCLUIDO: %d/%d processados, %d erros", processados, total, erros)
        logger.info("=" * 80)
        _finalizar_contexto_execucao(ctx, "concluido")
        _persistir_relatorio_execucao(ctx)

    except Exception as e:
        logger.error("[SCHEDULER] ERRO FATAL: %s", e)
        logger.error(traceback.format_exc())
        _registrar_erro_execucao(ctx, "fatal", "Erro fatal na execucao do scheduler", exc=e)
        _finalizar_contexto_execucao(ctx, "erro", motivo="erro_fatal")
        _persistir_relatorio_execucao(ctx)


# ===================================================================
# FUNCOES AUXILIARES
# ===================================================================

def _atualizar_item(sb, item_id, dados):
    """Atualiza um item na fila_admissao com retry para erros transientes (Cloudflare)"""
    for tentativa in range(3):
        try:
            sb.table('fila_admissao').update(dados).eq('id', str(item_id)).execute()
            return
        except Exception as e:
            if tentativa < 2:
                time.sleep(2 ** tentativa)  # backoff: 1s, 2s
            else:
                logger.error("[SCHEDULER] Erro ao atualizar item %s apos 3 tentativas: %s", item_id, e)


def _atualizar_sessao(sb, sessao_id, dados):
    """Atualiza a sessao na fila_sessao com retry para erros transientes (Cloudflare)"""
    for tentativa in range(3):
        try:
            sb.table('fila_sessao').update(dados).eq('id', sessao_id).execute()
            return
        except Exception as e:
            if tentativa < 2:
                time.sleep(2 ** tentativa)  # backoff: 1s, 2s
            else:
                logger.error("[SCHEDULER] Erro ao atualizar sessao %s apos 3 tentativas: %s", sessao_id, e)


def _processar_ocr_imagem(img):
    """Processa OCR de uma imagem via endpoint interno"""
    max_tentativas = 3

    for tentativa in range(1, max_tentativas + 1):
        if tentativa > 1:
            delay = (2 ** (tentativa - 1)) * 15
            logger.info("[SCHEDULER] OCR retry %d/%d - aguardando %ds...", tentativa, max_tentativas, delay)
            time.sleep(delay)

        try:
            resp = http_requests.post(f"{FLASK_BASE_URL}/api/ocr/processar", json={
                'imagemUrl': img.get('url', ''),
                'imagemNome': img.get('nome', ''),
            }, timeout=180)

            result = resp.json()

            # Rate limit - retry
            if resp.status_code == 500 and result.get('erro', '').find('429') >= 0:
                logger.warning("[SCHEDULER] Rate limit (429) na tentativa %d", tentativa)
                if tentativa < max_tentativas:
                    continue

            if resp.status_code == 200 and result.get('sucesso'):
                return {
                    'imagem': img.get('nome', ''),
                    'timestamp': datetime.now().isoformat(),
                    'dados': result.get('dados', {}),
                }
            else:
                logger.warning("[SCHEDULER] OCR falhou: %s", result.get('erro', 'desconhecido')[:200])
                if tentativa >= max_tentativas:
                    return None

        except Exception as e:
            logger.error("[SCHEDULER] Excecao OCR tentativa %d: %s", tentativa, e)
            if tentativa >= max_tentativas:
                return None

    return None


def _consolidar_resultados(resultados_ocr, cod_requisicao, dados_api):
    """Consolida resultados OCR via endpoint interno"""
    try:
        # Montar dados_api no formato que o endpoint espera
        dados_api_enviar = {}
        if dados_api:
            paciente = dados_api.get('paciente', {})
            requisicao = dados_api.get('requisicao', {})
            dados_api_enviar = {
                'paciente': paciente,
                'requisicao': requisicao,
                'convenio': dados_api.get('convenio', {}),
                'medico': dados_api.get('medico', {}),
                'localOrigem': dados_api.get('localOrigem', {}),
                'fontePagadora': dados_api.get('fontePagadora', {}),
            }

        resp = http_requests.post(f"{FLASK_BASE_URL}/api/consolidar-resultados", json={
            'resultados_ocr': resultados_ocr,
            'codRequisicao': cod_requisicao,
            'dados_api': dados_api_enviar,
        }, timeout=120)

        result = resp.json()

        if resp.status_code == 200 and result.get('sucesso'):
            logger.info("[SCHEDULER] Consolidacao OK para %s", cod_requisicao)
            return result.get('resultado')
        else:
            logger.warning("[SCHEDULER] Consolidacao falhou para %s: %s",
                           cod_requisicao, result.get('erro', '')[:200])
            return None

    except Exception as e:
        logger.error("[SCHEDULER] Erro ao consolidar %s: %s", cod_requisicao, e)
        return None


def _construir_form_data(dados_api, resultado_consolidado):
    """
    Constroi form_data_snapshot no mesmo formato que o frontend.
    Primeiro preenche com dados da API, depois sobrescreve com OCR.
    """
    form = {}

    if dados_api:
        requisicao = dados_api.get('requisicao', {})
        paciente = dados_api.get('paciente', {})
        convenio = dados_api.get('convenio', {})
        local_origem = dados_api.get('localOrigem', {})
        fonte_pagadora = dados_api.get('fontePagadora', {})

        # Data de coleta - converter para ISO YYYY-MM-DD se necessário
        dta_coleta = requisicao.get('dtaColeta', '') or ''
        if dta_coleta and 'T' in str(dta_coleta):
            dta_coleta = str(dta_coleta).split('T')[0]
        # Converter DD/MM/YYYY → YYYY-MM-DD (formato retornado pelo APLIS)
        if dta_coleta and '/' in str(dta_coleta):
            dta_coleta = _converter_data_iso(str(dta_coleta))

        form = {
            'codRequisicao': requisicao.get('codRequisicao', ''),
            'dtaColeta': dta_coleta,
            'idPaciente': str(paciente.get('idPaciente') or paciente.get('CodPaciente') or ''),
            'idConvenio': str(requisicao.get('idConvenio') or convenio.get('id') or ''),
            'idLocalOrigem': str(requisicao.get('idLocalOrigem') or local_origem.get('id') or '1'),
            'idFontePagadora': str(requisicao.get('idFontePagadora') or fonte_pagadora.get('id') or ''),
            'idMedico': str(requisicao.get('idMedico') or ''),
            'numGuia': str(requisicao.get('numGuia') or ''),
            'dadosClinicos': str(requisicao.get('dadosClinicos') or ''),
            'matConvenio': '',
            'examesConvenio': '',
            'fontePagadora': fonte_pagadora.get('nome', ''),
            'idLaboratorio': '1',
            'idUnidade': '1',
        }

        # Incluir info de sincronizacao 0085/0200 se disponivel
        sincronizacao = dados_api.get('sincronizacao', {})
        if sincronizacao and sincronizacao.get('sincronizado'):
            form['codRequisicaoCorrespondente'] = str(sincronizacao.get('codigo_correspondente', ''))
            form['tipoSincronizacao'] = str(sincronizacao.get('tipo_sincronizacao', ''))
            logger.info("[SCHEDULER] Sincronizacao 0085/0200: %s <-> %s",
                        form.get('codRequisicao'), form['codRequisicaoCorrespondente'])

    # Sobrescrever com dados do OCR consolidado
    if resultado_consolidado and resultado_consolidado.get('requisicoes'):
        req = resultado_consolidado['requisicoes'][0]

        # Data de coleta do OCR
        if req.get('requisicao', {}).get('dtaColeta', {}).get('valor'):
            dta = req['requisicao']['dtaColeta']['valor']
            form['dtaColeta'] = _converter_data_iso(dta)

        # Dados clinicos
        if req.get('requisicao', {}).get('dadosClinicos', {}).get('valor'):
            form['dadosClinicos'] = req['requisicao']['dadosClinicos']['valor']

        # Numero da guia
        if req.get('convenio', {}).get('numGuia', {}).get('valor'):
            form['numGuia'] = req['convenio']['numGuia']['valor']

        # Matricula do convenio
        if req.get('convenio', {}).get('matConvenio', {}).get('valor'):
            form['matConvenio'] = req['convenio']['matConvenio']['valor']

        # Fonte pagadora do OCR
        if req.get('convenio', {}).get('nome_fonte_pagadora', {}).get('valor'):
            form['fontePagadora'] = req['convenio']['nome_fonte_pagadora']['valor']

    # Fallback: data de coleta = hoje
    if not form.get('dtaColeta'):
        form['dtaColeta'] = datetime.now().strftime('%Y-%m-%d')

    return form


def _construir_patient_data(dados_api, resultado_consolidado):
    """
    Constroi patient_data_snapshot no mesmo formato que o frontend.
    """
    if not dados_api:
        return None

    paciente = dados_api.get('paciente', {})
    requisicao = dados_api.get('requisicao', {})
    convenio = dados_api.get('convenio', {})
    local_origem = dados_api.get('localOrigem', {})
    fonte_pagadora = dados_api.get('fontePagadora', {})
    medico = dados_api.get('medico', {})

    # Calcular idade
    idade_str = ''
    dta_nasc = paciente.get('dtaNasc', '')
    if dta_nasc:
        try:
            if 'T' in str(dta_nasc):
                dta_nasc = str(dta_nasc).split('T')[0]
            dt = datetime.strptime(str(dta_nasc), '%Y-%m-%d')
            idade = relativedelta(datetime.now(), dt).years
            idade_str = f"{idade} anos"
        except Exception:
            idade_str = ''

    # Formatar data DD/MM/YYYY
    birth_date_fmt = ''
    if dta_nasc:
        try:
            parts = str(dta_nasc).split('-')
            if len(parts) == 3:
                birth_date_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            birth_date_fmt = str(dta_nasc)

    # Formatar data de coleta
    dta_coleta = requisicao.get('dtaColeta', '')
    coleta_fmt = ''
    if dta_coleta:
        try:
            d = str(dta_coleta).split('T')[0] if 'T' in str(dta_coleta) else str(dta_coleta)
            parts = d.split('-')
            if len(parts) == 3:
                coleta_fmt = f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            coleta_fmt = str(dta_coleta)

    # CRM formatado
    crm_str = ''
    if medico.get('crm'):
        crm_str = f"CRM: {medico['crm']}/{medico.get('uf', '')}"

    patient = {
        'idPaciente': paciente.get('idPaciente') or paciente.get('CodPaciente') or '',
        'name': paciente.get('nome') or '',
        'age': idade_str,
        'birthDate': birth_date_fmt,
        'recordNumber': requisicao.get('codRequisicao') or '',
        'origin': local_origem.get('nome') or '',
        'payingSource': fonte_pagadora.get('nome') or '',
        'insurance': convenio.get('nome') or '',
        'doctorName': medico.get('nome') or '',
        'doctorCRM': crm_str or '',
        'collectionDate': coleta_fmt,
        'statusText': 'Em andamento',
        'status': 'in-progress',
        'cpf': paciente.get('cpf') or '',
        'sexo': paciente.get('sexo') or paciente.get('DesSexo') or '',
        'rg': paciente.get('rg') or '',
        'phone': paciente.get('telCelular') or '',
        'email': paciente.get('email') or '',
        'insuranceCardNumber': paciente.get('matriculaConvenio') or '',
        'numGuia': paciente.get('numGuia') or requisicao.get('numGuia') or '',
        'address': _formatar_endereco(paciente.get('endereco') or ''),
        'exams': requisicao.get('examesNomes') or '',
    }

    # Sobrescrever com dados do OCR
    if resultado_consolidado and resultado_consolidado.get('requisicoes'):
        req = resultado_consolidado['requisicoes'][0]

        if req.get('convenio', {}).get('nomeConvenio', {}).get('valor'):
            patient['insurance'] = req['convenio']['nomeConvenio']['valor']

        if req.get('convenio', {}).get('nome_fonte_pagadora', {}).get('valor'):
            patient['payingSource'] = req['convenio']['nome_fonte_pagadora']['valor']

    return patient


def _enriquecer_form_com_exames(form_data, resultado_consolidado):
    """
    Busca nomes de exames do OCR e preenche no formData.
    Replica preencherFormularioComOCR do frontend.
    """
    if not resultado_consolidado or not resultado_consolidado.get('requisicoes'):
        return

    req = resultado_consolidado['requisicoes'][0]
    itens_exame = req.get('requisicao', {}).get('itens_exame', [])

    if not itens_exame or not isinstance(itens_exame, list):
        return

    # Extrair nomes dos exames
    nomes = []
    for ex in itens_exame:
        if isinstance(ex, dict):
            nome = ex.get('descricao_ocr') or ex.get('descricao') or str(ex)
        else:
            nome = str(ex)
        if nome:
            nomes.append(nome)

    if not nomes:
        return

    form_data['examesConvenio'] = ', '.join(nomes)
    logger.info("[SCHEDULER] Exames extraidos do OCR: %s", ', '.join(nomes))

    # Buscar IDs dos exames no banco
    try:
        resp = http_requests.post(f"{FLASK_BASE_URL}/api/exames/buscar-por-nome", json={
            'nomes_exames': nomes,
        }, timeout=30)

        if resp.status_code == 200:
            result = resp.json()
            if result.get('sucesso') and result.get('resultados'):
                ids = [r['idExame'] for r in result['resultados'] if r.get('encontrado') and r.get('idExame')]
                if ids:
                    form_data['idExame'] = str(ids[0])
                    logger.info("[SCHEDULER] %d/%d exames encontrados no banco", len(ids), len(nomes))
    except Exception as e:
        logger.warning("[SCHEDULER] Erro ao buscar IDs de exames: %s", e)


def _formatar_endereco(endereco):
    """Converte endereco (dict ou string) para string legivel."""
    if not endereco:
        return ''
    if isinstance(endereco, str):
        return endereco
    if isinstance(endereco, dict):
        partes = [
            endereco.get('logradouro', ''),
            endereco.get('numEndereco', ''),
            endereco.get('complemento', ''),
            endereco.get('bairro', ''),
            endereco.get('cidade', ''),
            endereco.get('uf', ''),
            endereco.get('cep', ''),
        ]
        return ', '.join(p for p in partes if p)
    return str(endereco)


def _converter_data_iso(data_str):
    """Converte data DD/MM/YYYY para YYYY-MM-DD"""
    if not data_str:
        return ''
    data_str = str(data_str).strip()
    # Ja esta em ISO
    if len(data_str) == 10 and data_str[4] == '-':
        return data_str
    # DD/MM/YYYY
    if '/' in data_str:
        parts = data_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return data_str
