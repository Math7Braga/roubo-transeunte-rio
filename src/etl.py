"""ETL da série de roubo a transeunte no Município do Rio de Janeiro.

Entrada : tabela "ano x mês" publicada no Data.Rio (CSV ou XLSX), em
          ``data/raw/``.
Saída   : ``data/processed/`` com tabelas mensal (formato longo) e anual,
          em Parquet e CSV.gz, mais um relatório de qualidade (JSON).

Princípios: o arquivo bruto nunca é alterado; toda linha descartada ou
inconsistência encontrada é registrada em ``qa_report.json``.

Uso:
    python -m src.etl                       # usa o único arquivo de data/raw
    python -m src.etl --raw data/raw/x.csv  # arquivo explícito
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]

_MESES_ABREV = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
                "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
_MESES_NOME = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4,
               "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
               "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
MESES = {**_MESES_ABREV, **_MESES_NOME}

CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
EXTENSOES_BRUTO = {".csv", ".txt", ".xlsx", ".xls"}
_NULOS = {"", "-", "--", "..", "...", "nd", "n/d", "na", "nan", "none"}
_MILHAR = re.compile(r"^-?\d{1,3}(\.\d{3})+$")
_ANO = re.compile(r"^\s*((?:19|20)\d{2})(?!\d)")


# --------------------------------------------------------------------------
# Utilidades de texto e número
# --------------------------------------------------------------------------
def normalizar_texto(valor) -> str:
    """Minúsculas, sem acentos nem pontuação (para comparar rótulos)."""
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return ""
    s = unicodedata.normalize("NFKD", str(valor))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def to_number(valor) -> float:
    """Converte texto em número aceitando formatos brasileiros.

    "1.234" -> 1234 | "1.234,5" -> 1234.5 | "12,5" -> 12.5 | "-" -> NaN
    """
    if valor is None:
        return np.nan
    if isinstance(valor, (int, float, np.number)):
        return float(valor)
    s = str(valor).replace("\u00a0", " ").replace("\u2212", "-").strip()
    s = re.sub(r"[*†‡]+$", "", s.replace(" ", "")).replace("%", "")
    if s.lower() in _NULOS:
        return np.nan
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif _MILHAR.match(s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


# --------------------------------------------------------------------------
# Leitura do arquivo bruto
# --------------------------------------------------------------------------
def _detectar_separador(texto: str) -> str:
    """Escolhe o separador que mais produz linhas largas (>= 10 campos)."""
    linhas = [l for l in texto.splitlines() if l.strip()][:60]
    placar = {sep: sum(l.count(sep) >= 10 for l in linhas) for sep in (";", "\t", ",")}
    melhor = max(placar, key=placar.get)
    return melhor if placar[melhor] > 0 else ","


def ler_bruto(caminho: Path) -> list[pd.DataFrame]:
    """Lê CSV/XLSX como texto puro (sem inferir tipos). Retorna uma ou mais abas."""
    caminho = Path(caminho)
    if caminho.suffix.lower() in {".xlsx", ".xls"}:
        # calamine lê .xls (formato antigo) e .xlsx sem depender do xlrd (descontinuado)
        abas = pd.read_excel(caminho, sheet_name=None, header=None, dtype=str, engine="calamine")
        return list(abas.values())
    erro = None
    for enc in CODIFICACOES:
        try:
            texto = caminho.read_text(encoding=enc)
            break
        except UnicodeDecodeError as e:
            erro = e
    else:
        raise erro
    linhas = list(csv.reader(io.StringIO(texto), delimiter=_detectar_separador(texto)))
    largura = max(len(l) for l in linhas)
    return [pd.DataFrame([l + [""] * (largura - len(l)) for l in linhas], dtype=object)]


# --------------------------------------------------------------------------
# Interpretação da tabela larga (ano nas linhas, meses nas colunas)
# --------------------------------------------------------------------------
def localizar_cabecalho(df: pd.DataFrame, minimo: int = 6) -> int | None:
    """Índice da linha que contém os nomes dos meses (>= ``minimo`` meses)."""
    for i in range(len(df)):
        if sum(normalizar_texto(c) in MESES for c in df.iloc[i]) >= minimo:
            return i
    return None


def _classificar(rotulo: str) -> str | None:
    """Reconhece colunas anuais pelo rótulo (o "%" deve ter virado "pct" antes)."""
    if re.search(r"taxa|100 ?mil|cem mil", rotulo):
        return "taxa_100k_reportada"
    if re.search(r"popul|habitantes", rotulo):
        return "populacao"
    if re.search(r"difer|variac", rotulo):
        return "variacao_pct_reportada" if re.search(r"pct|percent", rotulo) else "diferenca_reportada"
    if "total" in rotulo:
        return "total_reportado"
    return None


def interpretar_tabela(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Devolve (tabela larga numérica, log de decisões). Tenta também a transposta."""
    for tentativa, tabela in (("original", df), ("transposta", df.T.reset_index(drop=True))):
        i_cab = localizar_cabecalho(tabela)
        if i_cab is not None:
            break
    else:
        raise ValueError("Não encontrei uma linha de cabeçalho com os nomes dos meses "
                         "(jan, fev, ... ou janeiro, fevereiro, ...). Verifique o arquivo.")
    log = {"orientacao": tentativa, "linha_cabecalho": int(i_cab)}

    corpo = tabela.iloc[i_cab + 1:]
    anos_por_coluna = [corpo.iloc[:, j].map(lambda c: bool(_ANO.match(str(c)))).sum()
                       for j in range(tabela.shape[1])]
    col_ano = int(np.argmax(anos_por_coluna))

    colunas = {col_ano: "ano"}
    for j in range(tabela.shape[1]):
        mes = MESES.get(normalizar_texto(tabela.iat[i_cab, j]))
        if mes and j not in colunas:
            colunas[j] = mes
    for j in range(tabela.shape[1]):
        if j in colunas:
            continue
        acima = tabela.iat[i_cab - 1, j] if i_cab > 0 else ""
        rotulo = f"{acima} {tabela.iat[i_cab, j]}".replace("%", " pct ")
        nome = _classificar(normalizar_texto(rotulo))
        if nome and nome not in colunas.values():
            colunas[j] = nome

    linhas, descartadas = [], []
    for idx, linha in corpo.iterrows():
        m = _ANO.match(str(linha.iloc[col_ano]))
        if not m:
            if any(str(c).strip() for c in linha):
                descartadas.append({"linha": int(idx), "motivo": "sem ano na coluna de ano",
                                    "conteudo": " | ".join(str(c) for c in linha if str(c).strip())[:120]})
            continue
        reg = {"ano": int(m.group(1))}
        for j, nome in colunas.items():
            if nome != "ano":
                reg[nome] = to_number(linha.iloc[j])
        linhas.append(reg)

    largo = pd.DataFrame(linhas)
    duplicados = largo["ano"].duplicated(keep="first")
    if duplicados.any():
        log["anos_duplicados_descartados"] = largo.loc[duplicados, "ano"].tolist()
        largo = largo.loc[~duplicados]
    largo = largo.sort_values("ano").reset_index(drop=True)
    for mes in range(1, 13):
        if mes not in largo:
            largo[mes] = np.nan
    log["colunas_reconhecidas"] = {str(k): v for k, v in colunas.items()}
    log["linhas_descartadas"] = descartadas
    return largo, log


# --------------------------------------------------------------------------
# Transformações
# --------------------------------------------------------------------------
def para_formato_longo(largo: pd.DataFrame) -> pd.DataFrame:
    """Largo (ano x 12 meses) -> longo (uma linha por ano-mês com valor)."""
    longo = largo.melt(id_vars="ano", value_vars=list(range(1, 13)),
                       var_name="mes", value_name="ocorrencias")
    longo["mes"] = longo["mes"].astype(int)
    longo = longo.dropna(subset=["ocorrencias"]).sort_values(["ano", "mes"])
    longo["data"] = pd.to_datetime({"year": longo["ano"], "month": longo["mes"], "day": 1})
    n_meses = longo.groupby("ano")["mes"].transform("count")
    longo["ano_parcial"] = n_meses < 12
    longo["ocorrencias"] = longo["ocorrencias"].astype("int64")
    return longo[["data", "ano", "mes", "ocorrencias", "ano_parcial"]].reset_index(drop=True)


def montar_anual(largo: pd.DataFrame, mensal: pd.DataFrame) -> pd.DataFrame:
    """Tabela anual com métricas derivadas e colunas reportadas na fonte."""
    anual = (mensal.groupby("ano")
             .agg(meses_validos=("mes", "count"), total_calculado=("ocorrencias", "sum"))
             .reset_index())
    anual["ano_completo"] = anual["meses_validos"] == 12
    extras = [c for c in ("total_reportado", "diferenca_reportada", "variacao_pct_reportada",
                          "populacao", "taxa_100k_reportada") if c in largo]
    anual = anual.merge(largo[["ano", *extras]], on="ano", how="left")
    for c in ("total_reportado", "diferenca_reportada", "variacao_pct_reportada",
              "populacao", "taxa_100k_reportada"):
        if c not in anual:
            anual[c] = np.nan
    completo = anual["ano_completo"]
    anual["taxa_100k_calculada"] = np.where(
        completo, anual["total_calculado"] / anual["populacao"] * 1e5, np.nan)
    ant = anual["total_calculado"].shift(1).where(completo & completo.shift(1, fill_value=False))
    anual["diferenca_calculada"] = anual["total_calculado"] - ant
    anual["variacao_pct"] = (anual["diferenca_calculada"] / ant * 100)
    return anual


def validar(largo: pd.DataFrame, anual: pd.DataFrame) -> dict:
    """Confere a tabela derivada contra os valores reportados (sem alterar dados)."""
    qa = {}
    comp = anual.dropna(subset=["total_reportado"])
    ruim = comp[(comp["total_reportado"] - comp["total_calculado"]).abs() > 0.5]
    qa["total_divergente_da_soma_dos_meses"] = ruim[["ano", "total_reportado", "total_calculado"]].to_dict("records")
    comp = anual.dropna(subset=["taxa_100k_reportada", "taxa_100k_calculada"])
    rel = (comp["taxa_100k_reportada"] - comp["taxa_100k_calculada"]).abs() / comp["taxa_100k_calculada"]
    qa["taxa_divergente_mais_de_1pct"] = comp.loc[rel > 0.01, ["ano", "taxa_100k_reportada", "taxa_100k_calculada"]].to_dict("records")
    comp = anual.dropna(subset=["variacao_pct_reportada", "variacao_pct"])
    dif = (comp["variacao_pct_reportada"] - comp["variacao_pct"]).abs()
    qa["variacao_pct_divergente_mais_de_0_1pp"] = comp.loc[dif > 0.1, ["ano", "variacao_pct_reportada", "variacao_pct"]].to_dict("records")
    meses = largo.set_index("ano")[list(range(1, 13))]
    lacunas = []
    for ano, linha in meses.iterrows():
        validos = np.flatnonzero(linha.notna().to_numpy())
        if len(validos) and (np.diff(validos) > 1).any():
            lacunas.append(int(ano))
    qa["anos_com_lacuna_no_meio"] = lacunas
    qa["anos_parciais"] = anual.loc[~anual["ano_completo"], "ano"].tolist()
    qa["valores_negativos"] = int((meses < 0).sum().sum())
    return qa


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def encontrar_bruto(pasta: Path) -> Path:
    candidatos = sorted(p for p in Path(pasta).iterdir()
                        if p.suffix.lower() in EXTENSOES_BRUTO and not p.name.startswith("."))
    if len(candidatos) != 1:
        raise FileNotFoundError(
            f"Esperava exatamente 1 arquivo (.csv/.xlsx) em {pasta}, achei {len(candidatos)}. "
            "Baixe a tabela do Data.Rio e coloque-a lá (veja data/raw/LEIA-ME.md).")
    return candidatos[0]


def executar(raw: Path | None = None, saida: Path | None = None) -> dict:
    """Pipeline completo. Devolve {'mensal', 'anual', 'qa'}."""
    raw = Path(raw) if raw else encontrar_bruto(RAIZ / "data" / "raw")
    saida = Path(saida) if saida else RAIZ / "data" / "processed"
    saida.mkdir(parents=True, exist_ok=True)

    melhor, melhor_log = None, None
    for df in ler_bruto(raw):  # escolhe a aba com mais anos reconhecidos
        try:
            largo, log = interpretar_tabela(df)
        except ValueError:
            continue
        if melhor is None or len(largo) > len(melhor):
            melhor, melhor_log = largo, log
    if melhor is None:
        raise ValueError("Nenhuma aba/linha de cabeçalho com meses foi encontrada.")

    mensal = para_formato_longo(melhor)
    anual = montar_anual(melhor, mensal)
    qa = {"arquivo_bruto": raw.name, "sha256_bruto": sha256(raw),
          "interpretacao": melhor_log, "validacao": validar(melhor, anual),
          "n_registros_mensais": int(len(mensal)),
          "periodo": [str(mensal["data"].min().date()), str(mensal["data"].max().date())]}

    mensal.to_parquet(saida / "roubo_transeunte_mensal.parquet", index=False)
    anual.to_parquet(saida / "roubo_transeunte_anual.parquet", index=False)
    mensal.to_csv(saida / "roubo_transeunte_mensal.csv.gz", index=False)
    anual.to_csv(saida / "roubo_transeunte_anual.csv.gz", index=False)
    (saida / "qa_report.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"mensal": mensal, "anual": anual, "qa": qa}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--raw", type=Path, help="arquivo bruto (padrão: único arquivo em data/raw)")
    ap.add_argument("--out", type=Path, help="pasta de saída (padrão: data/processed)")
    args = ap.parse_args()
    r = executar(args.raw, args.out)
    print(f"OK: {len(r['mensal'])} registros mensais, {len(r['anual'])} anos "
          f"({r['qa']['periodo'][0]} a {r['qa']['periodo'][1]}).")
    for chave, valor in r["qa"]["validacao"].items():
        if valor:
            print(f"ATENÇÃO [{chave}]: {valor}")
