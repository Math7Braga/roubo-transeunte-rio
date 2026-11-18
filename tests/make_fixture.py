"""Gera uma tabela SINTÉTICA (dados inventados) no layout esperado do Data.Rio.

Serve apenas para testar o código. Nunca use estes números em análises ou no artigo.
"""
from __future__ import annotations

import numpy as np
from pathlib import Path

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _br(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_csv(destino: Path, ultimo_mes_2023: int = 10, seed: int = 7) -> Path:
    rng = np.random.default_rng(seed)
    linhas = ["Incidências de roubo a transeunte, por mês, segundo o ano;;;;;;;;;;;;;;;;",
              ";;;;;;;;;;;;;;;;",
              "Ano;" + ";".join(MESES) + ";Total;Diferença em relação ao ano anterior;População;Taxa por 100 mil habitantes"]
    sazon = 1 + 0.08 * np.cos((np.arange(12) - 11) / 12 * 2 * np.pi)
    anterior = None
    for ano in range(2003, 2024):
        nivel = 2200 + 40 * (ano - 2003) - 15 * max(0, ano - 2012) ** 1.6
        if ano in (2020, 2021):
            nivel *= 0.7
        meses = np.round(nivel * sazon * rng.normal(1, 0.04, 12)).astype(int)
        n = ultimo_mes_2023 if ano == 2023 else 12
        total = int(meses[:n].sum())
        pop = int(5_900_000 + 17_000 * (ano - 2003))
        taxa = total / pop * 1e5
        dif = "" if anterior is None else _br(total - anterior)
        cel = [_br(v) if i < n else "" for i, v in enumerate(meses)]
        rotulo = f"{ano}*" if ano == 2023 else str(ano)
        linhas.append(";".join([rotulo, *cel, _br(total), dif, _br(pop), _br(taxa, 1)]))
        anterior = total
    linhas += ["", "Fonte: dados fictícios para teste;;;;;;;;;;;;;;;;", "* Dados até outubro;;;;;;;;;;;;;;;;"]
    destino = Path(destino)
    destino.write_text("\n".join(linhas), encoding="cp1252")
    return destino
