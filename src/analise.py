"""Métricas e achados da análise exploratória (somente pandas/numpy)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]
MESES_EXT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def carregar(pasta: Path | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    pasta = Path(pasta) if pasta else RAIZ / "data" / "processed"
    mensal = pd.read_parquet(pasta / "roubo_transeunte_mensal.parquet")
    anual = pd.read_parquet(pasta / "roubo_transeunte_anual.parquet")
    return mensal, anual


def tendencia_linear(x, y) -> dict:
    """Reta de mínimos quadrados: inclinação por ano e R²."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    b, a = np.polyfit(x, y, 1)
    r2 = 1 - ((y - (a + b * x)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return {"inclinacao": float(b), "r2": float(r2)}


def indice_sazonal(mensal: pd.DataFrame) -> pd.DataFrame:
    """Índice sazonal: valor do mês / média mensal do próprio ano (anos completos).

    1,00 = mês na média do ano. Normalizar por ano remove o efeito do nível
    (que muda muito entre 2003 e hoje) e deixa só o padrão dentro do ano.
    """
    c = mensal[~mensal["ano_parcial"]].copy()
    c["indice"] = c["ocorrencias"] / c.groupby("ano")["ocorrencias"].transform("mean")
    c["acima"] = c["indice"] > 1
    return (c.groupby("mes")
            .agg(indice_medio=("indice", "mean"), desvio=("indice", "std"),
                 minimo=("indice", "min"), maximo=("indice", "max"),
                 anos_acima_da_media=("acima", "mean"))
            .reset_index())


def comparacao_ytd(mensal: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Acumulado jan..mês de corte (último mês disponível) para todos os anos."""
    ult = mensal["ano"].max()
    corte = int(mensal.loc[mensal["ano"] == ult, "mes"].max())
    sub = mensal[mensal["mes"] <= corte]
    ytd = (sub.groupby("ano").agg(n=("mes", "count"), ocorrencias=("ocorrencias", "sum"))
           .query("n == @corte").drop(columns="n").reset_index())
    return ytd, corte


def pivot_mensal(mensal: pd.DataFrame) -> pd.DataFrame:
    return mensal.pivot(index="ano", columns="mes", values="ocorrencias")


def comparacao_pandemia(mensal: pd.DataFrame, base=(2017, 2019), alvos=(2020, 2021, 2022)):
    """Razão mês a mês entre cada ano-alvo e a MEDIANA do mesmo mês no período-base.

    A mediana é robusta a um mês atípico isolado no período-base (com só 3 anos,
    um valor anômalo distorceria muito a média).
    """
    p = pivot_mensal(mensal)
    anos_base = [a for a in range(base[0], base[1] + 1) if a in p.index]
    if len(anos_base) < 2:
        return None
    ref = p.loc[anos_base].median()
    razoes = {a: (p.loc[a] / ref) for a in alvos if a in p.index}
    return {"base": ref, "razoes": pd.DataFrame(razoes), "anos_base": anos_base}


def outliers_mensais(mensal: pd.DataFrame) -> pd.DataFrame:
    """Meses atípicos: razão entre o valor e a mediana móvel centrada (13 meses).

    Sinaliza com a regra de Tukey (1,5·IQR) sobre o log da razão.
    """
    s = mensal.set_index("data")["ocorrencias"].astype(float)
    med = s.rolling(13, center=True, min_periods=7).median()
    lr = np.log(s / med)
    q1, q3 = lr.quantile([.25, .75])
    iqr = q3 - q1
    out = lr[(lr < q1 - 1.5 * iqr) | (lr > q3 + 1.5 * iqr)]
    df = pd.DataFrame({"ocorrencias": s[out.index], "mediana_movel": med[out.index],
                       "razao": np.exp(out)})
    return df.reindex(df["razao"].sub(1).abs().sort_values(ascending=False).index)


def resumo_achados(mensal: pd.DataFrame, anual: pd.DataFrame) -> dict:
    """Todos os números citados no artigo, calculados em um só lugar."""
    A = {}
    comp = anual[anual["ano_completo"]].copy()
    A["ano_ini"], A["ano_fim_completo"] = int(comp["ano"].min()), int(comp["ano"].max())
    ult = mensal.sort_values("data").iloc[-1]
    A["ultimo_ano"], A["ultimo_mes"] = int(ult["ano"]), int(ult["mes"])
    A["ultimo_ano_parcial"] = bool(ult["ano_parcial"])
    A["n_meses"] = int(len(mensal))

    # RQ1 --- evolução anual
    i_max, i_min = comp["total_calculado"].idxmax(), comp["total_calculado"].idxmin()
    A["pico_ano"], A["pico_total"] = int(comp.loc[i_max, "ano"]), int(comp.loc[i_max, "total_calculado"])
    A["vale_ano"], A["vale_total"] = int(comp.loc[i_min, "ano"]), int(comp.loc[i_min, "total_calculado"])
    ini = comp.iloc[0]
    fim = comp.iloc[-1]
    A["total_ini"], A["total_fim"] = int(ini["total_calculado"]), int(fim["total_calculado"])
    A["var_ini_fim_pct"] = (fim["total_calculado"] / ini["total_calculado"] - 1) * 100
    A["queda_do_pico_pct"] = (fim["total_calculado"] / A["pico_total"] - 1) * 100
    t = tendencia_linear(comp["ano"], comp["total_calculado"])
    A["tendencia_total"] = t
    tem_taxa = comp["taxa_100k_calculada"].notna().sum() >= 3
    A["tem_taxa"] = bool(tem_taxa)
    if tem_taxa:
        ct = comp.dropna(subset=["taxa_100k_calculada"])
        j_max = ct["taxa_100k_calculada"].idxmax()
        A["taxa_pico_ano"] = int(ct.loc[j_max, "ano"])
        A["taxa_pico"] = float(ct.loc[j_max, "taxa_100k_calculada"])
        A["taxa_fim"] = float(ct.iloc[-1]["taxa_100k_calculada"])
        A["taxa_ini"] = float(ct.iloc[0]["taxa_100k_calculada"])
        A["pop_ini"], A["pop_fim"] = float(ct.iloc[0]["populacao"]), float(ct.iloc[-1]["populacao"])
        A["tendencia_taxa"] = tendencia_linear(ct["ano"], ct["taxa_100k_calculada"])
        A["spearman_taxa_ano"] = float(ct["ano"].rank().corr(ct["taxa_100k_calculada"].rank()))  # Spearman = Pearson dos postos
    pos = comp[comp["ano"] > A["pico_ano"]]
    if len(pos):
        k = pos["total_calculado"].idxmin()
        A["vale_pos_pico_ano"], A["vale_pos_pico_total"] = int(pos.loc[k, "ano"]), int(pos.loc[k, "total_calculado"])
    t = comp.set_index("ano")["total_calculado"]
    loc = t[(t > t.shift(1)) & (t > t.shift(-1)) & (t >= 0.8 * t.max())]
    A["picos_locais"] = [(int(a), int(v)) for a, v in loc.items()]
    v19 = comp.loc[comp["ano"] == 2019, "variacao_pct"]
    if len(v19) and v19.notna().all():
        A["var_2019_pct"] = float(v19.iloc[0])
    vc = comp["variacao_pct"].dropna()
    A["anos_de_queda"] = int((vc < 0).sum())
    A["anos_de_alta"] = int((vc > 0).sum())
    A["maior_alta_ano"] = int(comp.loc[vc.idxmax(), "ano"]); A["maior_alta_pct"] = float(vc.max())
    A["maior_queda_ano"] = int(comp.loc[vc.idxmin(), "ano"]); A["maior_queda_pct"] = float(vc.min())
    A["cv_anual_pct"] = float(comp["total_calculado"].std() / comp["total_calculado"].mean() * 100)

    # RQ2 --- sazonalidade
    s = indice_sazonal(mensal)
    A["saz"] = s
    a, b = s.loc[s["indice_medio"].idxmax()], s.loc[s["indice_medio"].idxmin()]
    A["saz_pico_mes"], A["saz_pico_idx"] = int(a["mes"]), float(a["indice_medio"])
    A["saz_vale_mes"], A["saz_vale_idx"] = int(b["mes"]), float(b["indice_medio"])
    A["saz_amplitude_pct"] = (A["saz_pico_idx"] / A["saz_vale_idx"] - 1) * 100
    A["saz_pico_anos_acima_pct"] = float(a["anos_acima_da_media"] * 100)
    A["saz_fraca"] = bool((s["indice_medio"] - 1).abs().max() < s["desvio"].median())
    A["saz_desvio_med"] = float(s["desvio"].median())
    A["saz_afast_max"] = float((s["indice_medio"] - 1).abs().max())
    A["saz_n_anos"] = int(mensal.loc[~mensal["ano_parcial"], "ano"].nunique())
    rec = mensal[(~mensal["ano_parcial"]) & (mensal["ano"] >= A["ano_fim_completo"] - 4)]
    if rec["ano"].nunique() >= 3:
        sr = indice_sazonal(rec)
        A["saz_recente_pico_mes"] = int(sr.loc[sr["indice_medio"].idxmax(), "mes"])
        A["saz_recente_vale_mes"] = int(sr.loc[sr["indice_medio"].idxmin(), "mes"])

    # RQ3 --- pandemia
    cp = comparacao_pandemia(mensal)
    A["pandemia"] = cp
    if cp is not None:
        r = cp["razoes"]
        for ano in r.columns:
            A[f"razao_media_{ano}"] = float(r[ano].mean())
            A[f"razao_min_{ano}"] = float(r[ano].min())
            A[f"razao_min_mes_{ano}"] = int(r[ano].idxmin())
        A["pandemia_base"] = (cp["anos_base"][0], cp["anos_base"][-1])
        if 2020 in r.columns:
            A["razao_jan_fev_2020"] = float(r.loc[[1, 2], 2020].mean())

    # Acumulado até o último mês disponível
    ytd, corte = comparacao_ytd(mensal)
    A["ytd"], A["ytd_corte"] = ytd, corte
    ult_ytd = ytd.iloc[-1]
    A["ytd_ano"], A["ytd_valor"] = int(ult_ytd["ano"]), int(ult_ytd["ocorrencias"])
    if len(ytd) > 1:
        ant = ytd.iloc[-2]
        A["ytd_ant_ano"], A["ytd_ant_valor"] = int(ant["ano"]), int(ant["ocorrencias"])
        A["ytd_var_ant_pct"] = (ult_ytd["ocorrencias"] / ant["ocorrencias"] - 1) * 100
        k = ytd["ocorrencias"].idxmin()
        A["ytd_eh_minimo"] = bool(k == ytd.index[-1])
        A["ytd_pico_ano"] = int(ytd.loc[ytd["ocorrencias"].idxmax(), "ano"])
        A["ytd_pico_valor"] = int(ytd["ocorrencias"].max())

    # Outliers
    o = outliers_mensais(mensal)
    A["outliers"] = o
    A["n_outliers"] = int(len(o))
    fora = o[~o.index.year.isin([2020, 2021])]
    A["outlier_isolado"] = ({"data": fora.index[0], "ocorrencias": int(fora.iloc[0]["ocorrencias"]),
                             "razao": float(fora.iloc[0]["razao"])} if len(fora) else None)
    return A
