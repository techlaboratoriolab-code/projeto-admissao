import csv
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

        data_evento = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d").date()
        if data_evento < START or data_evento > END:
            index += 1
            continue

        block = [current]
        index += 1
        while index < total and PATH_MARKER not in lines[index]:
            block.append(lines[index].rstrip("\n"))
            index += 1

        yield timestamp_match.group(1), timestamp_match.group(2), block


def extract_event(data, hora, block, source_file):
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

    possui_sucesso = any(SUCCESS_RE.search(line) for line in block)

    if possui_sucesso:
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
        "timestamp": f"{data} {hora}",
        "data": data,
        "cod_requisicao": cod_requisicao,
        "status": status,
        "detalhe": detalhe,
        "arquivo_log": source_file,
    }


def main():
    eventos = []

    for file_path in LOG_FILES:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as log_file:
                lines = log_file.readlines()
        except OSError:
            continue

        for data, hora, block in parse_blocks(lines):
            evento = extract_event(data, hora, block, os.path.basename(file_path))
            if evento:
                eventos.append(evento)

    eventos.sort(key=lambda item: item["timestamp"])

    output_dir = "docs/relatorios"
    os.makedirs(output_dir, exist_ok=True)

    csv_path = os.path.join(output_dir, "sara_requisicoes_2026-03-23_a_2026-03-27.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["timestamp", "data", "cod_requisicao", "status", "detalhe", "arquivo_log"],
        )
        writer.writeheader()
        writer.writerows(eventos)

    salvos = sum(1 for item in eventos if item["status"] == "salvo")
    erros = sum(1 for item in eventos if item["status"] == "erro")

    md_path = os.path.join(output_dir, "sara_requisicoes_2026-03-23_a_2026-03-27.md")
    with open(md_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Relatório semanal - api.sara\n\n")
        md_file.write("- Período: 2026-03-23 até 2026-03-27\n")
        md_file.write(f"- Total de tentativas: {len(eventos)}\n")
        md_file.write(f"- Salvas: {salvos}\n")
        md_file.write(f"- Com erro: {erros}\n\n")
        md_file.write("## Detalhes\n\n")
        md_file.write("| Timestamp | Cod Requisição | Status | Detalhe | Log |\n")
        md_file.write("|---|---|---|---|---|\n")

        for item in eventos:
            detalhe = (item["detalhe"] or "").replace("|", "/")
            md_file.write(
                f"| {item['timestamp']} | {item['cod_requisicao']} | {item['status']} | {detalhe} | {item['arquivo_log']} |\n"
            )

    print(f"CSV={csv_path}")
    print(f"MD={md_path}")
    print(f"TOTAL={len(eventos)} SALVOS={salvos} ERROS={erros}")


if __name__ == "__main__":
    main()
