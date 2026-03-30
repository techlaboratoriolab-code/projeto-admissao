import glob
import os
import re
from datetime import date, datetime

START = date(2026, 3, 23)
END = date(2026, 3, 27)

LOG_FILES = sorted(glob.glob("backend/logs/api_admissao.log*"))

START_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})")
SUCCESS_RE = re.compile(r"\[SalvarAdmissao\].*Sucesso! CodRequisicao:\s*([^\s|]+)")
COD_RE = re.compile(r'"codRequisicao"\s*:\s*"?([^"\s,}]+)"?')
ERROR_RE = re.compile(
    r'(?:msgErro"\s*:\s*"([^"]+)")|(?:\[SalvarAdmissao\]\s*[^:]*:\s*(.*))'
)

PATH_MARKER = "Path: /api/admissao/salvar"
CRED_MARKER = "Credenciais apLIS: usuario=api.sara"


def parse_blocks(lines):
    index = 0
    total = len(lines)

    while index < total:
        current = lines[index].rstrip("\n")
        if PATH_MARKER not in current:
            index += 1
            continue

        timestamp_match = START_RE.match(current)
        if not timestamp_match:
            index += 1
            continue

        event_date = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d").date()
        if event_date < START or event_date > END:
            index += 1
            continue

        block = [current]
        index += 1
        while index < total and PATH_MARKER not in lines[index]:
            block.append(lines[index].rstrip("\n"))
            index += 1

        yield timestamp_match.group(1), timestamp_match.group(2), block


def extract_event(data, hour, block, source_file):
    if not any(CRED_MARKER in line for line in block):
        return None

    cod_requisicao = ""
    for line in block:
        success_match = SUCCESS_RE.search(line)
        if success_match:
            cod_requisicao = success_match.group(1).strip()
            break

    if not cod_requisicao:
        for line in block:
            cod_match = COD_RE.search(line)
            if cod_match:
                cod_requisicao = cod_match.group(1).strip()
                break

    if any(SUCCESS_RE.search(line) for line in block):
        status = "salvo"
        detalhe = ""
    else:
        status = "erro"
        detalhe = ""
        for line in block:
            error_match = ERROR_RE.search(line)
            if error_match:
                detalhe = (error_match.group(1) or error_match.group(2) or "").strip()
                if detalhe:
                    break

        if not detalhe:
            for line in block:
                if "Resposta com sucesso != 1" in line:
                    detalhe = line.strip()
                    break

        if not detalhe:
            detalhe = "Erro sem detalhe explícito no bloco de log"

    return {
        "timestamp": f"{data} {hour}",
        "data": data,
        "cod_requisicao": cod_requisicao,
        "status": status,
        "detalhe": detalhe,
        "arquivo_log": source_file,
        "bloco": block,
    }


def main():
    events = []

    for file_path in LOG_FILES:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
        except OSError:
            continue

        for data, hour, block in parse_blocks(lines):
            event = extract_event(data, hour, block, os.path.basename(file_path))
            if event:
                events.append(event)

    events.sort(key=lambda item: item["timestamp"])

    output_dir = "docs/relatorios"
    os.makedirs(output_dir, exist_ok=True)

    output_path = os.path.join(output_dir, "sara_requisicoes_2026-03-23_a_2026-03-27_completo.log")

    total = len(events)
    total_saved = sum(1 for item in events if item["status"] == "salvo")
    total_error = sum(1 for item in events if item["status"] == "erro")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("RELATÓRIO COMPLETO - API.SARA\n")
        file.write("PERÍODO: 2026-03-23 até 2026-03-27\n")
        file.write(f"TOTAL: {total} | SALVOS: {total_saved} | ERROS: {total_error}\n")
        file.write("=" * 120 + "\n\n")

        for index, event in enumerate(events, start=1):
            file.write(f"EVENTO #{index}\n")
            file.write(f"Timestamp: {event['timestamp']}\n")
            file.write(f"CodRequisicao: {event['cod_requisicao']}\n")
            file.write(f"Status: {event['status']}\n")
            file.write(f"Detalhe: {event['detalhe']}\n")
            file.write(f"Arquivo de origem: {event['arquivo_log']}\n")
            file.write("-" * 120 + "\n")
            file.write("BLOCO BRUTO:\n")
            for line in event["bloco"]:
                file.write(line + "\n")
            file.write("=" * 120 + "\n\n")

    print(f"OUTPUT={output_path}")
    print(f"TOTAL={total} SALVOS={total_saved} ERROS={total_error}")


if __name__ == "__main__":
    main()
