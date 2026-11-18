"""Gera docs/index.html (artigo) e as figuras a partir de data/processed/.

    python -m src.build_article
Todos os números do texto vêm de ``analise.resumo_achados``: se os dados mudam,
o artigo muda junto (nada é digitado à mão).
"""
from __future__ import annotations

import html
import inspect
import re
from datetime import date
from pathlib import Path
from string import Template


from . import analise, config, etl, visualizacao as viz
from .analise import MESES_EXT

RAIZ = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------- formatação
def n(v, c=0):  # 1.234,5
    return f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pc(v, c=1):  # 12,3%
    return f"{n(v, c)}%"


def en(v, c=0):  # 1,234.5
    return f"{v:,.{c}f}"


def palavras(texto: str) -> int:
    return len(re.sub(r"<[^>]+>", "", texto).split())


MESES_EN = ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]


# ---------------------------------------------------------------- textos
def periodo(A):
    fim = f"{MESES_EXT[A['ultimo_mes'] - 1]} de {A['ultimo_ano']}"
    return f"{A['ano_ini']}–{A['ultimo_ano']}", f"janeiro de {A['ano_ini']} a {fim}"


def resumo_pt(A):
    achados = (f"Nos anos completos, o total anual passou de {n(A['total_ini'])} em {A['ano_ini']} para "
               f"{n(A['total_fim'])} em {A['ano_fim_completo']}, com máximo de {n(A['pico_total'])} em "
               f"{A['pico_ano']}. O índice sazonal foi mais alto em {MESES_EXT[A['saz_pico_mes'] - 1]} "
               f"({n(A['saz_pico_idx'], 2)}) e mais baixo em {MESES_EXT[A['saz_vale_mes'] - 1]} "
               f"({n(A['saz_vale_idx'], 2)}).")
    if A["saz_fraca"]:
        achados += " Esse padrão sazonal é fraco diante da variação entre os anos."
    if "razao_media_2020" in A:
        b = A["pandemia_base"]
        achados += (f" Em 2020, o volume mensal médio correspondeu a {pc(A['razao_media_2020'] * 100, 0)} "
                    f"da mediana mensal de {b[0]}–{b[1]}")
        achados += (f" e, em 2022, a {pc(A['razao_media_2022'] * 100, 0)}." if "razao_media_2022" in A else ".")
    return (
        "O roubo a transeunte afeta diretamente a circulação das pessoas pela cidade, e acompanhar sua "
        "evolução ajuda a avaliar a segurança nos espaços públicos. Este estudo analisa a série mensal de "
        f"ocorrências no Município do Rio de Janeiro, de {periodo(A)[1]}, publicada como dado aberto no "
        "portal Data.Rio. Construímos um pipeline reprodutível em Python (pandas, NumPy, matplotlib e "
        "Plotly) que lê a tabela original, padroniza tipos e formatos, confere os totais e as taxas "
        "publicados e calcula medidas derivadas: variação anual, índice sazonal e comparação com um "
        f"período-base. {achados} Como os dados são agregados para o município e vêm de registros de "
        "ocorrência, os resultados descrevem padrões temporais e não permitem atribuir causas. Código, "
        "dados processados e dicionário de variáveis estão abertos, conforme os princípios FAIR, para "
        "que qualquer pessoa possa auditar e ampliar a análise.")


def resumo_en(A):
    achados = (f"In complete years, annual totals went from {en(A['total_ini'])} in {A['ano_ini']} to "
               f"{en(A['total_fim'])} in {A['ano_fim_completo']}, peaking at {en(A['pico_total'])} in "
               f"{A['pico_ano']}. The seasonal index was highest in {MESES_EN[A['saz_pico_mes'] - 1]} "
               f"({A['saz_pico_idx']:.2f}) and lowest in {MESES_EN[A['saz_vale_mes'] - 1]} "
               f"({A['saz_vale_idx']:.2f}).")
    if A["saz_fraca"]:
        achados += " This seasonal pattern is weak compared with year-to-year variation."
    if "razao_media_2020" in A:
        b = A["pandemia_base"]
        achados += (f" In 2020 the average monthly volume was {A['razao_media_2020'] * 100:.0f}% of the "
                    f"{b[0]}–{b[1]} monthly median")
        achados += (f" and, in 2022, {A['razao_media_2022'] * 100:.0f}%." if "razao_media_2022" in A else ".")
    return (
        "Pedestrian robbery directly affects how people move around the city, and tracking it helps "
        "assess safety in public spaces. This study analyzes the monthly series of recorded incidents in "
        f"the municipality of Rio de Janeiro, Brazil, from January {A['ano_ini']} to "
        f"{MESES_EN[A['ultimo_mes'] - 1]} {A['ultimo_ano']}, published as open data on the Data.Rio portal. "
        "We built a reproducible Python pipeline (pandas, NumPy, matplotlib and Plotly) that reads the "
        "original table, standardizes types and formats, cross-checks the published totals and rates, and "
        f"computes derived measures: annual change, a seasonal index and a comparison with a baseline "
        f"period. {achados} Because the data are aggregated at municipal level and come from police "
        "records, the results describe temporal patterns and do not support causal claims. Code, "
        "processed data and a data dictionary are openly available under the FAIR principles so that "
        "anyone can audit and extend the analysis.")


def texto_rq1(A):
    var = A["var_ini_fim_pct"]
    t = [f"Considerando apenas anos completos, o total anual passou de {n(A['total_ini'])} ocorrências em "
         f"{A['ano_ini']} para {n(A['total_fim'])} em {A['ano_fim_completo']} "
         f"({'queda' if var < 0 else 'alta'} de {pc(abs(var))}). O valor máximo foi registrado em "
         f"{A['pico_ano']} ({n(A['pico_total'])}) e o mínimo em {A['vale_ano']} ({n(A['vale_total'])})"
         + (", no início da série" if A["vale_ano"] == A["ano_ini"] else "")
         + (f"; depois do pico, o menor total foi o de {A['vale_pos_pico_ano']} ({n(A['vale_pos_pico_total'])}). "
            if "vale_pos_pico_ano" in A else ". ") +
         f"Em relação ao pico, o último ano completo está {pc(abs(A['queda_do_pico_pct']))} "
         f"{'abaixo' if A['queda_do_pico_pct'] < 0 else 'acima'}."]
    if len(A["picos_locais"]) >= 2:
        lista = ", ".join(f"{ano} ({n(v)})" for ano, v in A["picos_locais"])
        t.append(f"A série não é monótona: há ondas de alta e queda, com máximos locais em {lista}.")
    t.append(f"Dentre as variações anuais, {A['anos_de_queda']} foram quedas e {A['anos_de_alta']} foram altas; "
             f"a maior alta ocorreu em {A['maior_alta_ano']} ({pc(A['maior_alta_pct'])}) e a maior queda em "
             f"{A['maior_queda_ano']} ({pc(A['maior_queda_pct'])}). O coeficiente de variação do total anual "
             f"é de {pc(A['cv_anual_pct'])}.")
    tt = A["tendencia_total"]
    ajuste = ("uma reta descreve bem a série" if tt["r2"] >= .6 else
              "uma reta descreve mal a série, o que sugere mudanças de regime ao longo do período")
    t.append(f"Uma regressão linear sobre o total anual tem inclinação de {n(tt['inclinacao'], 0)} "
             f"ocorrências por ano e R² de {n(tt['r2'], 2)}: {ajuste}.")
    if A["tem_taxa"]:
        cp = (A["pop_fim"] / A["pop_ini"] - 1) * 100
        t.append(f"Ajustando pelo tamanho da população, a taxa por 100 mil habitantes foi de "
                 f"{n(A['taxa_ini'], 1)} em {A['ano_ini']} para {n(A['taxa_fim'], 1)} em {A['ano_fim_completo']}, "
                 f"com máximo de {n(A['taxa_pico'], 1)} em {A['taxa_pico_ano']}. A população da série cresceu "
                 f"{pc(cp)} no período; por isso a taxa e o total absoluto contam histórias diferentes quando "
                 f"a população muda. A correlação de Spearman entre ano e taxa é {n(A['spearman_taxa_ano'], 2)}, "
                 "o que mede a direção monotônica geral, e não a existência de picos e vales intermediários.")
    return t


def texto_rq2(A):
    amp = A["saz_amplitude_pct"]
    grau = "modesta" if amp < 15 else "moderada" if amp < 30 else "pronunciada"
    t = [f"O índice sazonal médio é máximo em {MESES_EXT[A['saz_pico_mes'] - 1]} ({n(A['saz_pico_idx'], 2)}) e "
         f"mínimo em {MESES_EXT[A['saz_vale_mes'] - 1]} ({n(A['saz_vale_idx'], 2)}), uma diferença de "
         f"{pc(amp, 0)} entre o mês mais e o menos intenso: sazonalidade {grau}. Em "
         f"{pc(A['saz_pico_anos_acima_pct'], 0)} dos {A['saz_n_anos']} anos completos, "
         f"{MESES_EXT[A['saz_pico_mes'] - 1]} ficou acima da média do próprio ano, o que indica o quanto o "
         "padrão se repete de um ano para outro."]
    if A["saz_fraca"]:
        t.append(f"O desvio-padrão típico do índice (mediana entre os meses: {n(A['saz_desvio_med'], 2)}) é maior que o "
                 f"maior afastamento do índice médio em relação a 1,00 ({n(A['saz_afast_max'], 2)}). As barras de erro "
                 "da Figura 2 se sobrepõem: a diferença entre os meses é pequena diante da variação de um ano para "
                 "outro, e não há evidência de um calendário sazonal forte nesta série.")
    if "saz_recente_pico_mes" in A:
        igual = (A["saz_recente_pico_mes"] == A["saz_pico_mes"] and A["saz_recente_vale_mes"] == A["saz_vale_mes"])
        t.append("Restringindo aos cinco anos completos mais recentes, o pico fica em "
                 f"{MESES_EXT[A['saz_recente_pico_mes'] - 1]} e o vale em {MESES_EXT[A['saz_recente_vale_mes'] - 1]}"
                 + (", o mesmo padrão da série inteira." if igual else
                    ", diferente do padrão da série inteira, o que reforça que o padrão sazonal é instável."))
    return t


def texto_rq3(A):
    if A["pandemia"] is None:
        return ["A série não tem anos suficientes no período-base (2017–2019) para esta comparação."]
    b = A["pandemia_base"]
    t = [f"Para cada mês, comparamos o valor de 2020, 2021 e 2022 com a mediana do mesmo mês em {b[0]}–{b[1]}."]
    for ano in (2020, 2021, 2022):
        if f"razao_media_{ano}" in A:
            d = (A[f"razao_media_{ano}"] - 1) * 100
            t.append(f"Em {ano}, a média mensal ficou {pc(abs(d))} {'abaixo' if d < 0 else 'acima'} da base; a menor "
                     f"razão foi em {MESES_EXT[A[f'razao_min_mes_{ano}'] - 1]} "
                     f"({pc(A[f'razao_min_{ano}'] * 100, 0)} da base).")
    extra = ""
    if "razao_jan_fev_2020" in A and A["razao_jan_fev_2020"] < 0.95:
        extra = (f" A queda não começou com a pandemia: em janeiro e fevereiro de 2020, antes das medidas de "
                 f"isolamento, o volume já estava em {pc(A['razao_jan_fev_2020'] * 100, 0)} da base"
                 + (f", e o total de 2019 já havia caído {pc(abs(A['var_2019_pct']))} em relação a 2018."
                    if A.get("var_2019_pct", 0) < 0 else "."))
    return [" ".join(t) + extra]


def texto_discussao(A):
    ps = ["O dado mede <em>registros de ocorrência</em>, e não o crime em si. Mudanças na disposição de registrar, "
          "no acesso às delegacias ou nos canais de registro alteram a série sem que o número real de roubos mude. "
          "A própria fonte adverte que a classificação do crime feita pela Polícia Civil é provisória e pode ser "
          "alterada depois. Por isso, comparações entre extremos da série pedem cautela."]
    if A["maior_alta_pct"] >= 30:
        ps.append(f"A série tem saltos grandes: a maior alta anual foi a de {A['maior_alta_ano']} "
                  f"({pc(A['maior_alta_pct'])}) e a maior queda a de {A['maior_queda_ano']} ({pc(abs(A['maior_queda_pct']))}). "
                  "Variações dessa magnitude podem refletir mudanças reais, mas também alterações na forma de "
                  "registrar ou classificar os crimes; este estudo não investiga essas causas.")
    oi = A.get("outlier_isolado")
    if oi:
        d = oi["data"]
        ps.append(f"{MESES_EXT[d.month - 1].capitalize()} de {d.year} ({n(oi['ocorrencias'])} ocorrências) ficou em "
                  f"{pc(oi['razao'] * 100, 0)} da mediana móvel dos meses vizinhos. Um desvio isolado desse tamanho "
                  "pode refletir falha ou atraso de registro ou de consolidação, mas não temos como confirmar. Mantivemos "
                  "o valor, sem corrigi-lo, e usamos a mediana (e não a média) como base da comparação da pandemia, "
                  "justamente para que um mês assim não distorça o resultado.")
    ps.append("Total e taxa respondem a perguntas diferentes: o total mede o volume que o sistema de segurança precisa "
              "tratar, e a taxa mede o risco médio por habitante. Quando a população cresce, o mesmo total implica taxa "
              "menor, e é a taxa que permite comparar anos distantes.")
    if A["pandemia"] is not None and "razao_media_2022" in A:
        r22 = A["razao_media_2022"]
        if r22 >= 0.9:
            ps.append("A queda durante a pandemia é compatível com a restrição de circulação e a redução do fluxo de "
                      "pedestres, e a volta do volume ao patamar anterior é compatível com a retomada da circulação. "
                      "É uma hipótese, pois não temos dados de mobilidade para testá-la.")
        else:
            ps.append(f"Em 2022, o volume ainda estava {pc((1 - r22) * 100, 0)} abaixo da base de {A['pandemia_base'][0]}–"
                      f"{A['pandemia_base'][1]}, e o acumulado de {A['ytd_ano']} segue baixo. Ou seja, a queda não foi revertida "
                      "quando as restrições acabaram, e a pandemia, sozinha, não explica o nível atual. Como parte da "
                      "queda é anterior a 2020, outras explicações são plausíveis: mudanças em políticas de segurança, nos "
                      "hábitos de circulação e de pagamento, na migração para outros tipos de crime e na forma de "
                      "registro. São hipóteses; este estudo não as testa.")
    if not A["saz_fraca"]:
        ps.append("Para a sazonalidade, o calendário (férias, festas de fim de ano e variações no fluxo de pessoas) é a "
                  "explicação mais direta, também sem teste formal.")
    return "".join(f"<p>{x}</p>" for x in ps)


def conclusao_rqs(A):
    d = A["queda_do_pico_pct"]
    rq1 = (f"<strong>RQ1.</strong> O total anual não seguiu uma tendência única: foi de {n(A['total_ini'])} em "
           f"{A['ano_ini']} para {n(A['total_fim'])} em {A['ano_fim_completo']}, passando por máximo em "
           f"{A['pico_ano']} ({n(A['pico_total'])}) e por ondas de alta e queda; o último ano completo está "
           f"{pc(abs(d))} {'abaixo' if d < 0 else 'acima'} do pico.")
    if A["saz_fraca"]:
        rq2 = (f"<strong>RQ2.</strong> A sazonalidade é fraca e instável: o índice vai de "
               f"{n(A['saz_vale_idx'], 2)} em {MESES_EXT[A['saz_vale_mes'] - 1]} a {n(A['saz_pico_idx'], 2)} em "
               f"{MESES_EXT[A['saz_pico_mes'] - 1]}, dentro da variação entre anos.")
    else:
        rq2 = (f"<strong>RQ2.</strong> O pico sazonal ocorre em {MESES_EXT[A['saz_pico_mes'] - 1]} e o vale em "
               f"{MESES_EXT[A['saz_vale_mes'] - 1]}.")
    if A["pandemia"] is None:
        rq3 = "<strong>RQ3.</strong> Sem anos suficientes no período-base para a comparação."
    else:
        b = A["pandemia_base"]
        rq3 = (f"<strong>RQ3.</strong> Em 2020, o volume mensal médio foi {pc(A['razao_media_2020'] * 100, 0)} da mediana de "
               f"{b[0]}–{b[1]}")
        if "razao_media_2022" in A:
            rq3 += (f" e seguiu baixo em 2021 ({pc(A['razao_media_2021'] * 100, 0)}) e 2022 "
                    f"({pc(A['razao_media_2022'] * 100, 0)})")
        rq3 += "."
        if A.get("razao_jan_fev_2020", 1) < 0.95:
            rq3 += " A queda já aparecia antes de março de 2020, então a pandemia não a explica sozinha."
    return " ".join((rq1, rq2, rq3))


def texto_ytd(A):
    if "ytd_var_ant_pct" not in A:
        return ""
    corte = MESES_EXT[A["ytd_corte"] - 1]
    v = A["ytd_var_ant_pct"]
    s = (f"No acumulado de janeiro a {corte}, {A['ytd_ano']} soma {n(A['ytd_valor'])} ocorrências, "
         f"{'queda' if v < 0 else 'alta'} de {pc(abs(v))} frente a {A['ytd_ant_ano']} ({n(A['ytd_ant_valor'])}). ")
    s += ("Esse é o menor acumulado do período para a série. " if A["ytd_eh_minimo"] else
          f"O maior acumulado para esse recorte foi o de {A['ytd_pico_ano']} ({n(A['ytd_pico_valor'])}). ")
    return s


def texto_outliers(A):
    if A["n_outliers"] == 0:
        return "Nenhum mês foi sinalizado como atípico pelo critério de Tukey."
    top = A["outliers"].head(3)
    itens = "; ".join(f"{MESES_EXT[d.month - 1]} de {d.year} ({pc(r.razao * 100, 0)} da mediana móvel)"
                      for d, r in top.iterrows())
    return (f"O critério de Tukey sinalizou {A['n_outliers']} meses como atípicos em relação à mediana "
            f"móvel de 13 meses. Os três maiores desvios: {itens}.")


def tabela_anual(anual):
    linhas = []
    for r in anual.itertuples():
        marca = "" if r.ano_completo else f" <small>(jan–{MESES_EXT[r.meses_validos - 1][:3]})</small>"
        var = "—" if r.variacao_pct != r.variacao_pct else pc(r.variacao_pct)
        pop = "—" if r.populacao != r.populacao else n(r.populacao)
        taxa = "—" if r.taxa_100k_calculada != r.taxa_100k_calculada else n(r.taxa_100k_calculada, 1)
        linhas.append(f"<tr><td>{r.ano}{marca}</td><td>{n(r.total_calculado)}</td><td>{var}</td>"
                      f"<td>{pop}</td><td>{taxa}</td></tr>")
    return ("<table><caption>Tabela 1 — Série anual. Variação e taxa só são calculadas para anos completos."
            "</caption><thead><tr><th>Ano</th><th>Ocorrências</th><th>Variação anual</th><th>População</th>"
            "<th>Taxa por 100 mil hab.</th></tr></thead><tbody>" + "".join(linhas) + "</tbody></table>")


def codigo(*funcoes):
    return "\n\n".join(inspect.getsource(f).rstrip() for f in funcoes)


# ---------------------------------------------------------------- página
CSS = """
:root{color-scheme:light;--tinta:#14202b;--suave:#4a5a69;--papel:#fcfdfe;--linha:#d6dee6;--azul:#0072B2;--azul-fundo:#e7f1f8;--codigo:#0f1b26}
*{box-sizing:border-box}html{scroll-padding-top:1rem}
body{margin:0;background:var(--papel);color:var(--tinta);font:1.0625rem/1.72 Charter,"Iowan Old Style","Palatino Linotype",Georgia,serif}
.pagina{max-width:50rem;margin:0 auto;padding:1.5rem 1.25rem 4rem}
h1,h2,h3,.meta,.btn,nav,table,figcaption,.selo{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
h1{font-size:clamp(1.6rem,4.5vw,2.3rem);line-height:1.2;margin:.5rem 0 1rem;letter-spacing:-.01em}
h2{font-size:1.4rem;margin:2.8rem 0 .6rem;padding-top:1rem;border-top:1px solid var(--linha)}
h3{font-size:1.1rem;margin:2rem 0 .3rem}
p{margin:.8rem 0}
.meta{color:var(--suave);font-size:.95rem;line-height:1.5;margin:.15rem 0}
.meta strong{color:var(--tinta)}
.selos{display:flex;flex-wrap:wrap;gap:.4rem;margin:1rem 0}
.selo{font-size:.78rem;padding:.15rem .55rem;border:1px solid var(--linha);border-radius:.3rem;color:var(--suave)}
.btn{display:inline-block;margin:.6rem 0 0;padding:.55rem 1rem;background:var(--azul);color:#fff;text-decoration:none;border-radius:.35rem;font-weight:600;font-size:.95rem}
.btn:hover{background:#005a8c}
a{color:var(--azul)}a:focus-visible,.btn:focus-visible{outline:3px solid #E69F00;outline-offset:2px}
nav ul{list-style:none;display:flex;flex-wrap:wrap;gap:.3rem 1.1rem;padding:0;margin:1.4rem 0 0;font-size:.92rem}
.resumo{background:var(--azul-fundo);border-left:4px solid var(--azul);padding:.2rem 1.1rem;margin:1.6rem 0}
.resumo h2{border:0;margin:1rem 0 0;padding:0;font-size:1.1rem}
.chaves{color:var(--suave);font-size:.95rem}
figure{margin:1.8rem 0}figure img{width:100%;height:auto;display:block}
figcaption{font-size:.88rem;color:var(--suave);margin-top:.4rem;line-height:1.45}
.interativo{width:100%;overflow:hidden}
.rolagem{overflow-x:auto;margin:1.2rem 0}
table{border-collapse:collapse;width:100%;font-size:.9rem;font-variant-numeric:tabular-nums}
caption{text-align:left;color:var(--suave);padding-bottom:.4rem;font-size:.88rem}
th,td{padding:.3rem .6rem;border-bottom:1px solid var(--linha);text-align:right;white-space:nowrap}
th:first-child,td:first-child{text-align:left}th{border-bottom:2px solid var(--tinta)}
pre{background:var(--codigo);color:#e6edf3;padding:1rem;border-radius:.4rem;overflow-x:auto;font-size:.82rem;line-height:1.5}
code{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
p code,li code{background:#eef2f6;padding:.05rem .3rem;border-radius:.2rem;font-size:.88em}
ol.refs{padding-left:1.2rem}ol.refs li{margin:.5rem 0;overflow-wrap:anywhere}
.pular{position:absolute;left:-999px}.pular:focus{left:1rem;top:1rem;background:#fff;padding:.4rem}
footer{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--linha);font-size:.85rem;color:var(--suave)}
@media (max-width:40rem){body{font-size:1rem}.pagina{padding:1rem .9rem 3rem}}
"""

PAGINA = Template("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$titulo_txt</title>
<meta name="description" content="$descricao">
<meta name="author" content="$autores_txt">
<meta name="keywords" content="$chaves_txt">
<link rel="canonical" href="$pages">
<style>$css</style>
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<div class="pagina">
<header>
<h1>$titulo</h1>
<p class="meta"><strong>$autores</strong></p>
<p class="meta">$curso — $instituicao</p>
<p class="meta">Disciplina: $disciplina · Semestre $semestre</p>
<p class="meta">Professor orientador: <strong>$professor</strong></p>
<div class="selos" aria-label="Metadados"><span class="selo">Python 3</span><span class="selo">Código: MIT</span><span class="selo">Dados e texto: CC-BY 4.0</span><span class="selo">FAIR</span><span class="selo">Dados: $periodo_curto</span></div>
<a class="btn" href="$repo">Ver o repositório no GitHub</a>
<nav aria-label="Seções"><ul><li><a href="#resumo">Resumo</a></li><li><a href="#introducao">1. Introdução</a></li><li><a href="#metodologia">2. Metodologia</a></li><li><a href="#resultados">3. Resultados</a></li><li><a href="#conclusao">4. Conclusão</a></li><li><a href="#fair">5. Dados e FAIR</a></li><li><a href="#referencias">6. Referências</a></li></ul></nav>
</header>
<main id="conteudo">

<section class="resumo" id="resumo">
<h2>Resumo</h2>
<p>$resumo_pt</p>
<p class="chaves"><strong>Palavras-chave:</strong> $chaves.</p>
<h2>Abstract</h2>
<p lang="en">$resumo_en</p>
<p class="chaves" lang="en"><strong>Keywords:</strong> pedestrian robbery; public safety; Rio de Janeiro; time series; seasonality; open data.</p>
</section>

<section id="introducao">
<h2>1. Introdução</h2>
<p>Roubo a transeunte é a subtração de bens de uma pessoa a pé, mediante violência ou grave ameaça. Junto com o roubo de aparelho celular e o roubo em coletivo, compõe os chamados roubos de rua, indicadores acompanhados pelo Instituto de Segurança Pública do Estado do Rio de Janeiro (ISP-RJ, [s.d.]). Por acontecer no espaço público e no trajeto cotidiano, esse crime pesa na decisão de quando e por onde as pessoas circulam, e entender seu comportamento no tempo ajuda a orientar o debate sobre segurança urbana.</p>
<p>O portal Data.Rio publica a Tabela 2296, com dados do ISP e tabulação do Instituto Pereira Passos (IPP): ocorrências por mês, total anual, diferença em relação ao ano anterior (absoluta e percentual), população e taxa por cem mil habitantes (DATA.RIO, 2023). Este trabalho transforma essa tabela em uma série analisável e reprodutível, e responde a três perguntas de pesquisa:</p>
<ul>
<li><strong>RQ1.</strong> Como evoluíram o total anual e a taxa por 100 mil habitantes de roubo a transeunte no município desde $ano_ini, e em que anos ficaram o máximo e o mínimo?</li>
<li><strong>RQ2.</strong> Existe um padrão sazonal estável ao longo do ano? Quais meses concentram mais e menos ocorrências?</li>
<li><strong>RQ3.</strong> Como os anos de pandemia (2020 e 2021) e o ano seguinte se comparam com o patamar de 2017–2019?</li>
</ul>
</section>

<section id="metodologia">
<h2>2. Metodologia e Pipeline de Dados</h2>
<h3>2.1 Fonte e granularidade</h3>
<p>A fonte primária é a Tabela 2296 do Data.Rio (dados do Instituto de Segurança Pública, ISP; tabulação do IPP), que cobre $periodo_longo para o município inteiro, em arquivo Excel (<code>.xls</code>). A unidade observada é o número de ocorrências registradas por mês (granularidade mensal, agregação municipal). Os dados originais ficam em <code>data/raw/</code> e nunca são alterados; $n_meses valores mensais passam pelo pipeline.</p>
<h3>2.2 Tratamento dos dados</h3>
<ul>
<li><strong>Leitura.</strong> Tudo é lido como texto, para que nenhuma conversão aconteça sem controle. O código lê o Excel (ou CSV, tentando várias codificações), localiza a linha de cabeçalho pelos nomes dos meses e reconhece as colunas anuais pelo rótulo, ignorando os dígitos de nota de rodapé colados aos títulos (como “Total1”).</li>
<li><strong>Tipos.</strong> Números em formato brasileiro (<code>1.234,5</code>) são convertidos para ponto flutuante; os marcadores da fonte para dado indisponível (<code>...</code>) ou não aplicável (<code>..</code>), traços e células vazias viram valor ausente.</li>
<li><strong>Valores ausentes.</strong> Meses sem dado não são imputados: ficam fora da tabela mensal. Um ano com menos de 12 meses é marcado como parcial e excluído das comparações anuais.</li>
<li><strong>Estrutura.</strong> A tabela larga (ano × mês) vira formato longo (uma linha por mês), com a data real do primeiro dia do mês.</li>
<li><strong>Validação.</strong> O total e a taxa publicados na fonte são recalculados a partir dos meses e da população; divergências são registradas em <code>data/processed/qa_report.json</code>, sem corrigir nada em silêncio.</li>
<li><strong>Métricas derivadas.</strong> Variação anual (%), taxa por 100 mil habitantes, índice sazonal, razão em relação ao período-base e meses atípicos.</li>
</ul>
<h3>2.3 Métricas</h3>
<p>O <strong>índice sazonal</strong> divide cada mês pela média mensal do próprio ano e tira a média por mês nos anos completos; 1,00 significa um mês na média do ano. Os <strong>meses atípicos</strong> são os que ficam fora da regra de Tukey (1,5 × amplitude interquartil) aplicada ao log da razão entre o valor e a mediana móvel centrada de 13 meses (TUKEY, 1977). A comparação de <strong>pandemia</strong> usa a razão entre cada mês de 2020–2022 e a <em>mediana</em> do mesmo mês em 2017–2019; com apenas três anos na base, a mediana evita que um único mês atípico distorça o resultado.</p>
<h3>2.4 Trechos do pipeline</h3>
<pre><code>$codigo</code></pre>
</section>

<section id="resultados">
<h2>3. Resultados e Discussão</h2>

<h3>3.1 RQ1 — Evolução anual</h3>
$rq1
<div class="rolagem">$tabela</div>
<figure><img src="assets/fig1_evolucao_anual.png" alt="Gráfico de barras com o total anual de ocorrências e linha com a taxa por 100 mil habitantes" width="1800" height="1000" loading="lazy"><figcaption>Figura 1 — Total anual (barras) e taxa por 100 mil habitantes (linha), apenas anos completos. Fonte: elaboração própria a partir de Data.Rio.</figcaption></figure>

<h3>3.2 RQ2 — Sazonalidade</h3>
$rq2
<figure><img src="assets/fig3_sazonalidade.png" alt="Gráfico de barras com o índice sazonal médio de cada mês" width="1800" height="840" loading="lazy"><figcaption>Figura 2 — Índice sazonal médio por mês (1,00 = média do ano), com ±1 desvio-padrão. Fonte: elaboração própria.</figcaption></figure>
<script src="assets/plotly.min.js" charset="utf-8"></script>
<figure><div class="interativo">$fig_heatmap</div><figcaption>Figura 3 — Mapa de calor interativo das ocorrências por ano e mês (passe o mouse para ver os valores). Meses sem dado aparecem em branco. Fonte: elaboração própria.</figcaption></figure>
<p>Uma ressalva de método: o índice usa contagens brutas, sem ajuste pelo número de dias do mês. Fevereiro tem 28 ou 29 dias, cerca de 7% a menos que um mês de 30 dias, então parte de um índice baixo em fevereiro pode ser só calendário.</p>

<h3>3.3 RQ3 — Pandemia</h3>
$rq3
<figure><div class="interativo">$fig_pandemia</div><figcaption>Figura 4 — Razão entre o valor mensal e a mediana do período-base; abaixo de 100% significa menos ocorrências que o normal. Fonte: elaboração própria.</figcaption></figure>

<h3>3.4 Dados parciais e meses atípicos</h3>
<p>$ytd</p>
<p>$outliers</p>

<h3>3.5 Discussão</h3>
$discussao
</section>

<section id="conclusao">
<h2>4. Conclusão</h2>
<p>$conclusao_rqs</p>
<p><strong>Limitações.</strong> (i) A série é municipal e agregada: não mostra diferenças entre bairros ou áreas de policiamento. (ii) Os valores são registros de ocorrência e sofrem de subnotificação. (iii) A contagem mensal não é ajustada pelo número de dias. (iv) O último ano é parcial e não entra nas comparações anuais. (v) A população é uma projeção do ISP referente a dezembro ou ao último mês disponível do ano (julho, em 2022), conforme a nota da fonte; não auditamos essa estimativa. (vi) Não há inferência causal.</p>
<p><strong>Trabalhos futuros.</strong> Decompor a série com métodos como STL ou ajustar modelos ARIMA; testar o efeito de eventos específicos por análise de intervenção; cruzar com dados de mobilidade; repetir a análise por área de segurança pública; e comparar com os demais roubos de rua (celular e coletivo).</p>
</section>

<section id="fair">
<h2>5. Disponibilidade dos Dados e Declaração FAIR</h2>
<p>Este trabalho segue os princípios FAIR (WILKINSON et al., 2016). Repositório: <a href="$repo">$repo</a>.</p>
<div class="rolagem"><table><thead><tr><th>Princípio</th><th>Como é atendido</th></tr></thead><tbody>
<tr><td>Findable</td><td style="white-space:normal;text-align:left"><code>README.md</code> com resumo, palavras-chave e link da fonte; autoria, disciplina e instituição no cabeçalho.</td></tr>
<tr><td>Accessible</td><td style="white-space:normal;text-align:left">Repositório público; ingestão sem credenciais; artigo servido pelo GitHub Pages.</td></tr>
<tr><td>Interoperable</td><td style="white-space:normal;text-align:left"><code>data/data_dictionary.md</code>; dados processados em Parquet e CSV.gz.</td></tr>
<tr><td>Reusable</td><td style="white-space:normal;text-align:left">Código sob MIT; dados e texto sob CC-BY 4.0; <code>requirements.txt</code> com versões fixas.</td></tr>
</tbody></table></div>
<p>Para reproduzir o pipeline completo:</p>
<pre><code>git clone $repo.git
cd roubo-transeunte-rio
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# coloque a tabela baixada do Data.Rio em data/raw/
python -m src.etl                # gera data/processed/
python -m src.build_article      # gera docs/index.html e as figuras
pytest                           # testes automáticos</code></pre>
</section>

<section id="referencias">
<h2>6. Referências</h2>
<ol class="refs">
<li>DATA.RIO. <strong>Tabela 2296 – Incidências de roubo a transeunte, por mês, total, diferenças com relação ao ano anterior, população e taxa por cem mil habitantes segundo o ano, no Município do Rio de Janeiro entre Janeiro/2003 – Outubro/2023</strong>. Rio de Janeiro, 2023. Fonte dos dados: Instituto de Segurança Pública (ISP); cálculos e tabulação: IPP. Disponível em: <a href="$fonte">$fonte</a>. Acesso em: $acesso.</li>
<li>HARRIS, C. R. et al. Array programming with NumPy. <strong>Nature</strong>, v. 585, p. 357–362, 2020.</li>
<li>HUNTER, J. D. Matplotlib: a 2D graphics environment. <strong>Computing in Science &amp; Engineering</strong>, v. 9, n. 3, p. 90–95, 2007.</li>
<li>INSTITUTO DE SEGURANÇA PÚBLICA (ISP-RJ). <strong>ISPDados</strong>. Rio de Janeiro, [s.d.]. Disponível em: <a href="https://www.ispdados.rj.gov.br">https://www.ispdados.rj.gov.br</a>.</li>
<li>MCKINNEY, W. Data structures for statistical computing in Python. In: PYTHON IN SCIENCE CONFERENCE, 9., 2010, Austin. <strong>Proceedings</strong> [...]. 2010. p. 56–61.</li>
<li>PLOTLY. <strong>Plotly Python Graphing Library</strong>. Disponível em: <a href="https://plotly.com/python/">https://plotly.com/python/</a>.</li>
<li>TUKEY, J. W. <strong>Exploratory data analysis</strong>. Reading: Addison-Wesley, 1977.</li>
<li>WILKINSON, M. D. et al. The FAIR Guiding Principles for scientific data management and stewardship. <strong>Scientific Data</strong>, v. 3, art. 160018, 2016.</li>
</ol>
</section>
</main>
<footer>
<p>© $ano_copy $autores. Texto, figuras e dados processados licenciados sob <a href="$licenca">Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)</a>; texto legal em <a href="$licenca_legal">legalcode</a>. Código-fonte sob licença MIT. Material oferecido como está, sem garantias de qualquer tipo (Seção 5 da licença).</p>
<p>Baseado na Tabela 2296 do Data.Rio (dados do ISP; tabulação do IPP), <strong>modificada</strong>: os valores publicados foram preservados, reorganizados em formato longo e acrescidos de métricas derivadas. O uso dessas fontes não implica endosso por elas. Repositório: <a href="$repo">$repo</a>.</p>
<p>Página gerada por <code>src/build_article.py</code> em $hoje a partir dos dados em <code>data/processed/</code>.</p>
</footer>
</div>
</body>
</html>
""")


def construir(proc: Path | None = None, docs: Path | None = None) -> dict:
    docs = Path(docs) if docs else RAIZ / "docs"
    (docs / "assets").mkdir(parents=True, exist_ok=True)
    mensal, anual = analise.carregar(proc)
    A = analise.resumo_achados(mensal, anual)
    curto, longo = periodo(A)

    viz.fig_evolucao_anual(anual).savefig(docs / "assets" / "fig1_evolucao_anual.png")
    viz.fig_sazonalidade(A["saz"]).savefig(docs / "assets" / "fig3_sazonalidade.png")
    f2, f4 = viz.fig_heatmap(mensal), (viz.fig_pandemia(A["pandemia"]) if A["pandemia"] else None)
    # include_plotlyjs="directory" grava assets/plotly.min.js (mesma versão que gerou os gráficos)
    f2.write_html(docs / "assets" / "fig2_heatmap.html", include_plotlyjs="directory", config=viz._CFG)
    if f4:
        f4.write_html(docs / "assets" / "fig4_pandemia.html", include_plotlyjs="directory", config=viz._CFG)

    rq3 = texto_rq3(A)
    resumo = resumo_pt(A)
    p = {
        "titulo": html.escape(config.TITULO.format(periodo=curto)),
        "titulo_txt": html.escape(config.TITULO.format(periodo=curto)),
        "descricao": html.escape(resumo[:280]),
        "autores": ", ".join(html.escape(a) for a in config.AUTORES),
        "autores_txt": html.escape("; ".join(config.AUTORES)),
        "chaves": "; ".join(config.PALAVRAS_CHAVE), "chaves_txt": ", ".join(config.PALAVRAS_CHAVE),
        "curso": config.CURSO, "instituicao": config.INSTITUICAO, "disciplina": config.DISCIPLINA,
        "semestre": config.SEMESTRE, "professor": html.escape(config.PROFESSOR),
        "repo": config.REPO_URL, "pages": config.PAGES_URL, "ano_copy": config.COPYRIGHT_ANO,
        "licenca": config.LICENCA_URL, "licenca_legal": config.LICENCA_LEGAL_URL, "fonte": config.FONTE_URL, "acesso": config.DATA_ACESSO,
        "css": CSS, "periodo_curto": curto, "periodo_longo": longo, "ano_ini": A["ano_ini"],
        "ano_fim": A["ano_fim_completo"], "n_meses": n(A["n_meses"]),
        "resumo_pt": resumo, "resumo_en": resumo_en(A),
        "codigo": html.escape(codigo(etl.to_number, etl.para_formato_longo, analise.indice_sazonal)),
        "discussao": texto_discussao(A),
        "rq1": "".join(f"<p>{t}</p>" for t in texto_rq1(A)),
        "rq2": "".join(f"<p>{t}</p>" for t in texto_rq2(A)),
        "rq3": "".join(f"<p>{t}</p>" for t in rq3),
        "tabela": tabela_anual(anual),
        "fig_heatmap": viz.html_plotly(f2, "fig-heatmap"),
        "fig_pandemia": viz.html_plotly(f4, "fig-pandemia") if f4 else "<p>Sem dados suficientes.</p>",
        "ytd": texto_ytd(A), "outliers": texto_outliers(A),
        "pico_ano": A["pico_ano"], "vale_ano": A["vale_ano"],
        "mes_pico": MESES_EXT[A["saz_pico_mes"] - 1], "mes_vale": MESES_EXT[A["saz_vale_mes"] - 1],
        "conclusao_rqs": conclusao_rqs(A), "hoje": date.today().strftime("%d/%m/%Y"),
    }
    pagina = PAGINA.safe_substitute(p)
    (docs / "index.html").write_text(pagina, encoding="utf-8")
    return {"achados": A, "resumo_palavras": palavras(resumo), "abstract_palavras": palavras(resumo_en(A))}


if __name__ == "__main__":
    r = construir()
    print(f"docs/index.html gerado. Resumo: {r['resumo_palavras']} palavras; abstract: {r['abstract_palavras']}.")
    for campo, nome in ((r["resumo_palavras"], "Resumo"), (r["abstract_palavras"], "Abstract")):
        if not 150 <= campo <= 250:
            print(f"ATENÇÃO: {nome} fora do intervalo de 150 a 250 palavras.")
    if config.pendencias():
        print("ATENÇÃO: edite src/config.py — campos ainda com texto de exemplo:", ", ".join(config.pendencias()))
