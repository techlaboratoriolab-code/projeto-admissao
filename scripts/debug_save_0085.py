import glob
import re
from pathlib import Path

code = "0085081559005"
files = sorted(glob.glob("backend/logs/api_admissao.log*"))
pat_start = re.compile(r"^\d{4}-\d{2}-\d{2} .*Path: /api/admissao/salvar")

blocks = []
for fp in files:
    try:
        lines = Path(fp).read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        continue

    i = 0
    n = len(lines)
    while i < n:
        if pat_start.search(lines[i]):
            block = [lines[i]]
            i += 1
            while i < n and not pat_start.search(lines[i]):
                block.append(lines[i])
                i += 1
            if any(code in ln for ln in block):
                blocks.append((fp, block))
        else:
            i += 1

print("TOTAL_BLOCKS", len(blocks))
for index, (fp, block) in enumerate(blocks[-5:], start=1):
    print("\n" + "=" * 120)
    print(f"BLOCK {index} FILE {fp}")
    for line in block:
        lower = line.lower()
        if (
            "Path: /api/admissao/salvar" in line
            or "[SalvarAdmissao]" in line
            or "numGuia" in line
            or "matConvenio" in line
            or "MatConvenio" in line
            or "carteirinha" in lower
            or "guia" in lower
            or "Resposta com sucesso != 1" in line
            or "msgErro" in line
            or "ERRO DO apLIS" in line
        ):
            print(line)
