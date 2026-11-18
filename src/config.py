"""Metadados do artigo. EDITE os campos entre colchetes antes de publicar."""

TITULO = ("Roubo a transeunte no Município do Rio de Janeiro, {periodo}: "
          "tendência, sazonalidade e o período da pandemia de COVID-19")
AUTORES = ["Matheus Braga"]
CURSO = "Bacharelado em Sistemas de Informação — 6º período"
INSTITUICAO = "UniLaSalle RJ"
DISCIPLINA = "Linguagem de Programação (Análise e Visualização de Dados com Python)"
SEMESTRE = "2026/2"
PROFESSOR = "Alexandre Louzada"
REPO_URL = "https://github.com/Math7Braga/roubo-transeunte-rio"
PAGES_URL = "https://math7braga.github.io/roubo-transeunte-rio/"  # GitHub Pages usa minúsculas
COPYRIGHT_ANO = 2026
LICENCA_URL = "https://creativecommons.org/licenses/by/4.0/"                 # resumo (deed)
LICENCA_LEGAL_URL = "https://creativecommons.org/licenses/by/4.0/legalcode.en"  # texto legal oficial
DATA_ACESSO = "18 nov. 2026"  # ajuste para a data em que você baixou a tabela
FONTE_URL = "https://www.data.rio/documents/d66ec8e443e243ac9e4ab8d9d97c3235/about"
PALAVRAS_CHAVE = ["roubo a transeunte", "segurança pública", "Município do Rio de Janeiro",
                  "séries temporais", "sazonalidade", "dados abertos"]


def pendencias() -> list[str]:
    """Campos ainda com texto de exemplo (entre colchetes ou SEU-USUARIO)."""
    campos = {"AUTORES": " ".join(AUTORES), "PROFESSOR": PROFESSOR,
              "REPO_URL": REPO_URL, "PAGES_URL": PAGES_URL}
    return [k for k, v in campos.items() if "[" in v or "SEU-USUARIO" in v]
