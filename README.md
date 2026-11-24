# grobid-extractor

Ferramenta em Python para extrair, em lote, o conteúdo de artigos científicos em PDF. Ele usa o GROBID, uma ferramenta de aprendizado de máquina que identifica a estrutura de um artigo (título, autores, afiliações, resumo, seções do texto, figuras, tabelas e referências bibliográficas). 

O GROBID roda como servidor no Docker. Este repositório é responsável pelo envio dos PDFs a ele. O modelo oferece cinco serviços (endpoints), e você escolhe qual usar com a opção --endpoint. 

Serve para transformar uma coleção de artigos em dados estruturados e pesquisáveis. Isso é útil para montar corpora de revisões sistemáticas e bibliográficas, extrair metadados para catalogação, preparar textos para análise de texto e processamento de linguagem natural (PLN) e organizar bibliografias a partir dos PDFs.

## Requisitos

- Docker
- Python 3.10+

## Como rodar

1. Subir o GROBID:

```bash
docker compose up -d
```

2. Criar e ativar o ambiente Python (Windows/PowerShell):

```powershell
python -m venv .venv
```

```powershell
.venv\Scripts\Activate.ps1
```

```powershell
pip install -e .
```

3. Colocar os PDFs na pasta `PDFS/` e extrair:

```bash
grobid-extract --endpoint fulltext --input PDFS
```

Os resultados ficam em `output/<endpoint>/`.

## Endpoints

| `--endpoint` | Entrada | Retorna |
|---|---|---|
| `header` | PDF | título, autores, afiliações, resumo, palavras-chave |
| `fulltext` | PDF | documento completo: cabeçalho, seções, figuras, tabelas, referências |
| `references` | PDF | só a bibliografia |
| `citation` | `--citation "texto"` | uma referência estruturada |
| `citation-list` | `--citations-file refs.txt` | várias referências estruturadas |

## Formatos de saída

Escolha com `--format` (padrão: `tei json md`):

| Formato | Conteúdo |
|---|---|
| `tei` | XML bruto do GROBID |
| `json` | JSON estruturado |
| `clean` | JSON só com o texto narrativo (apenas `fulltext`) |
| `md` | Markdown |
| `txt` | texto puro (apenas `fulltext`) |

Exemplo:

```bash
grobid-extract --endpoint fulltext --input PDFS --format clean txt
```

Todas as opções:

```bash
grobid-extract --help
```

## Configuração (opcional)

Os padrões funcionam com o `docker compose` acima. Para mudar URL, porta, timeout ou concorrência, copie `.env.example` para `.env` e edite.
