# Dicionário de dados

Fonte: **Data.Rio — Tabela 2296** — *Incidências de roubo a transeunte, por mês, total, diferenças com
relação ao ano anterior, população e taxa por cem mil habitantes segundo o ano, no Município do Rio de
Janeiro entre Janeiro/2003 – Outubro/2023* (https://www.data.rio/documents/d66ec8e443e243ac9e4ab8d9d97c3235/about).

- **Dados originais:** Instituto de Segurança Pública (ISP) — http://www.ispdados.rj.gov.br/ (acesso registrado na tabela em 27/11/2023).
- **Cálculos e tabulação:** IPP, Coordenadoria Técnica de Informações da Cidade.
- **Granularidade:** município do Rio de Janeiro; ocorrências registradas por mês.
- **Licença da fonte:** não informada na página do conjunto de dados (consultado em 18/11/2026).

## 1. Arquivo bruto (`data/raw/2296.xls`)

Planilha Excel (formato `.xls`), aba `T 2296`: uma linha por ano, uma coluna por mês e colunas anuais.
Há linhas de título acima e notas abaixo; o ETL as ignora e registra em `qa_report.json`. Rótulos
trazem dígitos de nota de rodapé (ex.: `Total1`, `População2`).

| Coluna (bruto) | Significado | Tipo | Formato |
|---|---|---|---|
| Ano | Ano de referência | inteiro | `AAAA` |
| Jan … Dez | Ocorrências registradas no mês | inteiro | contagem; `..` = não se aplica, `...` = não disponível |
| Total | Soma das ocorrências do ano, segundo a fonte | inteiro | contagem |
| Diferença Absoluta | Total do ano menos o total do ano anterior | inteiro | pode ser negativo; `..` no primeiro ano e no ano parcial |
| Diferença % | Variação percentual do total em relação ao ano anterior | decimal | percentual, ponto decimal |
| População | Projeção de população do ISP: referente a dezembro ou ao último mês disponível do ano (em 2022, a última projeção divulgada refere-se a julho) | decimal | habitantes |
| Taxa por 100 mil hab | Ocorrências por 100 mil habitantes | decimal | ponto decimal |

## 2. `roubo_transeunte_mensal` (`.parquet` e `.csv.gz`)

Uma linha por mês com dado. Meses sem valor (por exemplo, nov/dez do último ano) não aparecem.

| Variável | Significado | Tipo | Formato / unidade |
|---|---|---|---|
| `data` | Primeiro dia do mês de referência | datetime | `AAAA-MM-01` |
| `ano` | Ano | int | `AAAA` |
| `mes` | Mês | int | 1 a 12 |
| `ocorrencias` | Roubos a transeunte registrados no mês | int | contagem |
| `ano_parcial` | O ano tem menos de 12 meses com dado | bool | `True`/`False` |

## 3. `roubo_transeunte_anual` (`.parquet` e `.csv.gz`)

Uma linha por ano. Colunas com sufixo `_reportado/_reportada` vêm da fonte; as `_calculado/_calculada`
são derivadas neste projeto.

| Variável | Significado | Tipo | Formato / unidade |
|---|---|---|---|
| `ano` | Ano | int | `AAAA` |
| `meses_validos` | Quantidade de meses com dado | int | 0 a 12 |
| `total_calculado` | Soma dos meses com dado | int | contagem |
| `ano_completo` | `meses_validos == 12` | bool | |
| `total_reportado` | Total publicado na fonte | float | contagem |
| `diferenca_reportada` | Diferença absoluta publicada na fonte | float | contagem |
| `variacao_pct_reportada` | Diferença percentual publicada na fonte | float | % |
| `populacao` | População da fonte | float | habitantes |
| `taxa_100k_reportada` | Taxa publicada na fonte | float | ocorrências / 100 mil hab. |
| `taxa_100k_calculada` | `total_calculado / populacao × 100 000` (só anos completos) | float | ocorrências / 100 mil hab. |
| `diferenca_calculada` | Total do ano menos o do ano anterior (só se ambos completos) | float | contagem |
| `variacao_pct` | `diferenca_calculada / total do ano anterior × 100` | float | % |

## 4. `qa_report.json`

Relatório de rastreabilidade gerado pelo ETL: nome e SHA-256 do arquivo bruto, linha de cabeçalho
encontrada, colunas reconhecidas, linhas descartadas (notas de rodapé etc.), anos parciais e
divergências entre valores reportados e recalculados.

## 5. Limitações conhecidas

- Os valores são **registros de ocorrência**: sujeitos a subnotificação e a mudanças no registro.
- Contagens mensais não são ajustadas pelo número de dias do mês.
- A população é uma projeção do ISP (dezembro ou último mês disponível; julho em 2022); a metodologia não foi auditada aqui.
- O mês de fevereiro de 2017 (1.419 ocorrências) destoa muito dos vizinhos; foi mantido sem correção e sinalizado como atípico.
- A fonte adverte que a classificação do crime pela Polícia Civil é provisória e pode ser alterada depois.
