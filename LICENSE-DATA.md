# Licença dos dados processados, do texto e das figuras

Copyright © 2026 Matheus Braga.

Estes materiais são licenciados sob **Creative Commons Atribuição 4.0 Internacional (CC BY 4.0)**:

- Resumo: https://creativecommons.org/licenses/by/4.0/
- **Texto legal oficial:** https://creativecommons.org/licenses/by/4.0/legalcode.en
  (o site da CC oferece também versões traduzidas; em caso de dúvida vale o texto oficial)

## O que esta licença cobre

- `data/processed/` (tabelas mensal e anual, relatório `qa_report.json`)
- `data/data_dictionary.md`
- `docs/` (artigo e figuras), `README.md` e demais documentação

**Não cobre:** o código (licença MIT, arquivo `LICENSE`) e o arquivo bruto `data/raw/2296.xls`
(ver "Dados de terceiros").

## Como dar o crédito (Seção 3 do texto legal)

Ao compartilhar estes materiais, inclusive modificados, mantenha: o nome do criador (Matheus Braga),
o aviso de copyright, o aviso de que estão sob CC BY 4.0 com o link da licença, o aviso de que são
oferecidos sem garantias (Seção 5), o link para o material e **a indicação de que você os modificou**,
se for o caso. Exemplo:

> *Roubo a transeunte no Município do Rio de Janeiro — dados processados e análise.* © 2026 Matheus
> Braga. Licenciado sob CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Disponível em
> https://github.com/Math7Braga/roubo-transeunte-rio. Material oferecido como está, sem garantias.
> Baseado na Tabela 2296 do Data.Rio (dados do ISP; tabulação do IPP), modificada: reorganizada em
> formato longo e acrescida de métricas derivadas, sem alterar os valores publicados.

## Modificações feitas sobre a Tabela 2296

- Leitura do arquivo Excel e reorganização da tabela larga (ano × mês) em formato longo.
- Conversão de tipos; marcadores `..` e `...` da fonte tratados como valor ausente.
- Descarte das linhas de título e de notas (registradas em `qa_report.json`).
- Colunas derivadas: `ano_parcial`, `total_calculado`, `ano_completo`, `taxa_100k_calculada`,
  `diferenca_calculada`, `variacao_pct`.
- Colunas publicadas pela fonte (`*_reportado/_reportada`) mantidas **sem alteração**, e conferidas
  contra os valores recalculados.
- Nenhum valor foi imputado, corrigido ou removido da série.

## Dados de terceiros

A Tabela 2296 é do Data.Rio, com dados do Instituto de Segurança Pública (ISP) e tabulação do Instituto
Pereira Passos (IPP). Este projeto não define a licença da fonte: antes de publicar, confirme os termos de
reuso na página do conjunto de dados e mantenha a atribuição a ela. O uso dos nomes Data.Rio, ISP e IPP
serve apenas para identificar a origem e **não indica aprovação** deles (Seção 2(a)(6) do texto legal).

## Sem garantias

Os materiais são oferecidos "como estão", sem garantias de qualquer tipo, nos termos da Seção 5 do texto
legal. Este arquivo não é aconselhamento jurídico.
