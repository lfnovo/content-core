# Issue #51 — Validate engine names at every config entry point

**PR:** https://github.com/lfnovo/content-core/pull/90 (branch `fix/issue-51`, base `main`)

## Resumo das mudanças

| Arquivo | Mudança |
|---|---|
| `src/content_core/config.py` | `document_engine` / `url_engine` passam a usar os `Literal`s `DocumentEngine` / `UrlEngine` já existentes em `common/types.py`. Pydantic rejeita valor inválido vindo de construtor, `CCORE_*` e do TOML, com mensagem listando os valores válidos. |
| `src/content_core/config.py` | `config_set` valida o valor coerdido contra o campo (vocabulário `Literal` + constraints como `audio_concurrency` ge/le) **antes** de escrever. `content-core config set url_engine jinaa` sai com erro e não escreve nada. `config delete` inalterado. |
| `src/content_core/processors/url/__init__.py` | `except (ValueError, ConfigurationError): raise` antes do `except Exception` genérico (ramo "#51 antes de #60" da spec). Falha de rede continua degradando para saída vazia até #60 remover o catch. |
| `src/content_core/mcp/server.py` | Para URL, o MCP setava **os dois** engines com o mesmo valor — com o `Literal`, `engine="firecrawl"` passaria a estourar `ValidationError`. Agora aplica o engine só ao lado cujo vocabulário ele pertence (URL pode resolver para documento, então `engine="docling"` seta só `document_engine`) e devolve erro claro para nome desconhecido. |
| `src/content_core/cli.py` | Vocabulários derivados de `common/types.py` via `get_args` em vez de sets hardcoded. Comportamento idêntico. |

Testes adicionados em `test_config_v2.py`, `test_config_file.py`, `test_url_engine_select.py`, `test_cli.py`, `test_mcp_v2.py`.
Dois testes existentes foram corrigidos porque o vocabulário fechado os invalidou: `test_singleton_picks_up_env` usava `CCORE_URL_ENGINE=bs4` (nunca foi nome de engine válido) e a asserção de forwarding do MCP.

`common/exceptions.py` não foi tocado (em desenvolvimento paralelo pela #52).

## Gate

`uv run pytest tests/unit tests/integration -v` → **375 passed** (local).
CI: `test (3.10)`, `test (3.11)`, `test (3.12)`, `package`, `claude-review` — todos verdes.

## Cubic

PENDENTE_CUBIC

## Riscos / pontos para o revisor

- **Config file legado**: um `~/.content-core/config.toml` com valor inválido (ex.: `url_engine = "bs4"`) agora faz `ContentCoreConfig()` estourar em vez de ser aceito silenciosamente. É exatamente o que a decisão "vocabulário fechado valida na porta de entrada" pede, mas é uma quebra visível para quem tinha lixo no arquivo. `content-core config list` e `config delete` continuam funcionando (leem o TOML direto), então há caminho de saída.
- **`mcp/server.py` fora da "Surface" da issue**: foi obrigatório — o `Literal` tornaria `engine="firecrawl"` sobre URL um erro de validação. A mudança também corrige um bug pré-existente: `engine="docling"` sobre URL setava `url_engine="docling"`, que o router rejeitava e o catch genérico transformava em conteúdo vazio.
- **`except ValueError` no `extract_from_url`** é intencionalmente amplo: se algum engine levantar `ValueError` por parsing, agora ele propaga em vez de degradar. É a direção que a #60 formaliza.
- `docling_output_format` também é vocabulário fechado na prática, mas ficou fora do escopo da #51.
