import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_fixture import gerar_csv  # noqa: E402
from src import analise, etl  # noqa: E402


@pytest.mark.parametrize("texto,esperado", [
    ("1.234", 1234), ("1.234,5", 1234.5), ("12,5", 12.5), ("2300", 2300),
    ("2300.0", 2300), ("-", None), ("", None), ("1 234", 1234), ("−5", -5)])
def test_to_number(texto, esperado):
    r = etl.to_number(texto)
    assert (pd.isna(r)) if esperado is None else r == pytest.approx(esperado)


def test_normalizar_texto():
    assert etl.normalizar_texto("  Março.") == "marco"
    assert etl.normalizar_texto(None) == ""


@pytest.fixture(scope="module")
def resultado(tmp_path_factory):
    d = tmp_path_factory.mktemp("dados")
    bruto = gerar_csv(d / "tabela.csv")
    return etl.executar(bruto, d / "proc"), d


def test_cabecalho_e_anos(resultado):
    r, _ = resultado
    assert r["anual"]["ano"].tolist() == list(range(2003, 2024))
    assert r["qa"]["interpretacao"]["linha_cabecalho"] == 2


def test_ano_parcial_sinalizado(resultado):
    r, _ = resultado
    a = r["anual"].set_index("ano")
    assert not a.loc[2023, "ano_completo"] and a.loc[2023, "meses_validos"] == 10
    assert a.loc[2022, "ano_completo"]
    assert pd.isna(a.loc[2023, "taxa_100k_calculada"])
    assert r["mensal"].query("ano == 2023")["ano_parcial"].all()


def test_validacao_sem_divergencias(resultado):
    v = resultado[0]["qa"]["validacao"]
    assert v["total_divergente_da_soma_dos_meses"] == []
    assert v["taxa_divergente_mais_de_1pct"] == []
    assert v["anos_com_lacuna_no_meio"] == []


def test_notas_de_rodape_registradas(resultado):
    desc = resultado[0]["qa"]["interpretacao"]["linhas_descartadas"]
    assert any("Fonte" in d["conteudo"] for d in desc)


def test_pipeline_deterministico(resultado):
    r, d = resultado
    r2 = etl.executar(d / "tabela.csv", d / "proc2")
    pd.testing.assert_frame_equal(r["mensal"], r2["mensal"])
    pd.testing.assert_frame_equal(r["anual"], r2["anual"])


def test_arquivos_gerados(resultado):
    _, d = resultado
    nomes = {p.name for p in (d / "proc").iterdir()}
    assert {"roubo_transeunte_mensal.parquet", "roubo_transeunte_anual.parquet",
            "roubo_transeunte_mensal.csv.gz", "roubo_transeunte_anual.csv.gz",
            "qa_report.json"} <= nomes


def test_xlsx_equivalente_ao_csv(resultado, tmp_path):
    _, d = resultado
    bruto = pd.read_csv(d / "tabela.csv", sep=";", header=None, dtype=str, encoding="cp1252")
    bruto.to_excel(tmp_path / "t.xlsx", header=False, index=False)
    r = etl.executar(tmp_path / "t.xlsx", tmp_path / "p")
    assert r["mensal"]["ocorrencias"].sum() == resultado[0]["mensal"]["ocorrencias"].sum()


def test_tabela_transposta(resultado, tmp_path):
    _, d = resultado
    bruto = pd.read_csv(d / "tabela.csv", sep=";", header=None, dtype=str, encoding="cp1252")
    bruto.T.to_csv(tmp_path / "t.csv", sep=";", header=False, index=False)
    r = etl.executar(tmp_path / "t.csv", tmp_path / "p")
    assert len(r["anual"]) == 21


def test_sem_meses_gera_erro(tmp_path):
    (tmp_path / "x.csv").write_text("a;b\n1;2\n")
    with pytest.raises(ValueError):
        etl.executar(tmp_path / "x.csv", tmp_path / "p")


def test_achados(resultado):
    r, _ = resultado
    A = analise.resumo_achados(r["mensal"], r["anual"])
    assert A["ano_fim_completo"] == 2022 and A["ytd_corte"] == 10
    assert 1 <= A["saz_pico_mes"] <= 12
    assert A["razao_media_2020"] < 1  # fixture sintética impõe queda em 2020
    assert A["saz"]["indice_medio"].mean() == pytest.approx(1, abs=0.05)


def test_artigo_html_gerado(resultado, tmp_path):
    """Constrói o artigo com dados SINTÉTICOS (só teste) e checa a estrutura normativa."""
    from html.parser import HTMLParser
    from src import build_article

    r, d = resultado
    out = build_article.construir(d / "proc", tmp_path)
    assert 150 <= out["resumo_palavras"] <= 250 and 150 <= out["abstract_palavras"] <= 250
    texto = (tmp_path / "index.html").read_text(encoding="utf-8")
    for sec in ("resumo", "introducao", "metodologia", "resultados", "conclusao", "fair", "referencias"):
        assert f'id="{sec}"' in texto
    for rq in ("RQ1", "RQ2", "RQ3"):
        assert rq in texto
    import re
    assert not re.findall(r"\$[a-z_]+", texto)
    assert "{n_ini_total}" not in texto and "$resumo" not in texto
    assert (tmp_path / "assets" / "fig1_evolucao_anual.png").stat().st_size > 10_000
    HTMLParser().feed(texto)


RAW_REAL = Path(__file__).resolve().parents[1] / "data" / "raw" / "2296.xls"


@pytest.mark.skipif(not RAW_REAL.exists(), reason="arquivo real não está em data/raw")
def test_arquivo_real_data_rio(tmp_path):
    """Tabela 2296 do Data.Rio (ISP/IPP): confere a leitura contra valores impressos na fonte."""
    r = etl.executar(RAW_REAL, tmp_path)
    a = r["anual"].set_index("ano")
    assert list(a.index) == list(range(2003, 2024))
    assert a.loc[2003, "total_calculado"] == 11064
    assert a.loc[2020, "total_calculado"] == 25356
    assert a.loc[2023, "meses_validos"] == 10 and not a.loc[2023, "ano_completo"]
    assert a.loc[2017, "total_reportado"] == 45518
    assert a.loc[2005, "variacao_pct_reportada"] == pytest.approx(69.5135, abs=1e-3)
    v = r["qa"]["validacao"]
    assert v["total_divergente_da_soma_dos_meses"] == []
    assert v["taxa_divergente_mais_de_1pct"] == []
    assert v["variacao_pct_divergente_mais_de_0_1pp"] == []
    assert len(r["mensal"]) == 250
