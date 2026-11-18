# Roubo a transeunte no Município do Rio de Janeiro

![Python](https://img.shields.io/badge/python-3.12-blue) ![Código: MIT](https://img.shields.io/badge/c%C3%B3digo-MIT-green) ![Dados e texto: CC BY 4.0](https://img.shields.io/badge/dados%20e%20texto-CC%20BY%204.0-lightgrey) ![FAIR](https://img.shields.io/badge/FAIR-compliant-orange)

Projeto final da disciplina **Linguagem de Programação (Análise e Visualização de Dados com Python)** —
Bacharelado em Sistemas de Informação, 6º período, UniLaSalle RJ, semestre 2026/2.

- **Autoria:** Matheus Braga
- **Professor orientador:** Alexandre Louzada
- **Repositório:** https://github.com/Math7Braga/roubo-transeunte-rio
- **Artigo (GitHub Pages):** https://math7braga.github.io/roubo-transeunte-rio/

## Resumo executivo

Pipeline determinístico em Python que transforma a Tabela 2296 do Data.Rio (incidências de roubo a
transeunte no Município do Rio de Janeiro, janeiro/2003 a outubro/2023; dados do ISP, tabulação do IPP) em uma série analisável e responde a
três perguntas de pesquisa:

1. **RQ1** — Como evoluíram o total anual e a taxa por 100 mil habitantes, e quando ficaram o máximo e o mínimo?
2. **RQ2** — Existe um padrão sazonal estável? Quais meses concentram mais e menos ocorrências?
3. **RQ3** — Como 2020, 2021 e 2022 se comparam com o patamar (mediana mensal) de 2017–2019?

O artigo em `docs/index.html` é **gerado a partir dos dados**: todos os números do texto são calculados
por `src/analise.py`, então ele nunca fica desatualizado em relação ao código.

**Palavras-chave:** roubo a transeunte; segurança pública; Município do Rio de Janeiro; séries temporais; sazonalidade; dados abertos.

## Fonte dos dados

Data.Rio — *Tabela 2296 – Incidências de roubo a transeunte, por mês, total, diferenças com relação ao ano
anterior, população e taxa por cem mil habitantes segundo o ano, no Município do Rio de Janeiro entre
Janeiro/2003 – Outubro/2023*. Dados originais: Instituto de Segurança Pública (ISP); cálculos e tabulação: IPP:
https://www.data.rio/documents/d66ec8e443e243ac9e4ab8d9d97c3235/about

## Estrutura

```
roubo-transeunte-rio/
├── README.md
├── LICENSE                  # MIT (código)
├── LICENSE-DATA.md          # CC BY 4.0 (dados processados e texto)
├── requirements.txt         # versões fixadas (pip freeze)
├── .gitignore
├── data/
│   ├── raw/2296.xls         # tabela original do Data.Rio (+ LEIA-ME.md)
│   ├── processed/           # Parquet, CSV.gz e qa_report.json (gerados pelo ETL)
│   └── data_dictionary.md
├── notebooks/analise_exploratoria.ipynb
├── src/
│   ├── etl.py               # leitura, limpeza, validação, persistência
│   ├── analise.py           # métricas e achados
│   ├── visualizacao.py      # figuras estáticas (matplotlib) e interativas (Plotly)
│   ├── build_article.py     # gera docs/index.html
│   └── config.py            # autores, professor, links (edite aqui)
├── tests/                   # pytest (usa dados SINTÉTICOS, só para testar o código)
└── docs/                    # artigo publicado no GitHub Pages
    ├── index.html
    └── assets/
```

## Como reproduzir

```bash
git clone https://github.com/Math7Braga/roubo-transeunte-rio.git
cd roubo-transeunte-rio
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (a tabela original já está em data/raw/2296.xls)
python -m src.etl                  # data/raw -> data/processed
python -m src.build_article        # data/processed -> docs/index.html + figuras
pytest                             # testes automáticos
# notebook (opcional): pip install jupyterlab && jupyter lab notebooks/analise_exploratoria.ipynb
```

O `requirements.txt` foi gerado com Python 3.12. Se o `pip install` falhar em outra versão do Python,
use o 3.12 ou recrie o arquivo com `pip freeze` no seu ambiente.

## Decisões de engenharia

- O arquivo bruto **nunca é alterado**; tudo é lido como texto e convertido de forma explícita.
- Valores ausentes **não são imputados**; anos com menos de 12 meses são marcados como parciais.
- Totais e taxas publicados são **recalculados e comparados**; divergências vão para `qa_report.json`.
- O hash SHA-256 do arquivo bruto é registrado para provar qual versão foi analisada.

## Licenças

| O quê | Licença |
|---|---|
| Código (`src/`, `tests/`, notebook) | [MIT](LICENSE) |
| Dados processados (`data/processed/`), dicionário, artigo (`docs/`), figuras e documentação | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — veja [LICENSE-DATA.md](LICENSE-DATA.md) |
| Dado bruto (`data/raw/2296.xls`) | Pertence à fonte (Data.Rio / ISP / IPP); não é relicenciado por este projeto |

Texto legal oficial da CC BY 4.0: https://creativecommons.org/licenses/by/4.0/legalcode.en

Os dados processados são uma **versão modificada** da Tabela 2296 (reorganizada em formato longo, com
métricas derivadas); os valores publicados não foram alterados. Detalhes em [LICENSE-DATA.md](LICENSE-DATA.md).

## Como citar

BRAGA, M. *Roubo a transeunte no Município do Rio de Janeiro*. UniLaSalle RJ, 2026.
Disponível em: https://github.com/Math7Braga/roubo-transeunte-rio.
