# Progresso — FoodOps AI

_Última atualização: 31/10/2026_

## ✅ O que já foi feito

Esqueleto do projeto criado (Fase 1 quase completa). Testes passando (7/7).

### Infraestrutura
| Arquivo | Conteúdo |
|---|---|
| `pyproject.toml` | Dependências base + extras opcionais `agent` (LangGraph), `rag` (ChromaDB, sentence-transformers) e `dev` (pytest, httpx) |
| `docker-compose.yml` | Postgres 16 + serviço da app |
| `Dockerfile` | Imagem Python 3.12 rodando uvicorn |
| `.env.example` | `DATABASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `CHROMA_PATH` |
| `.gitignore` | venv, `.env`, caches, `.chroma/` |

### Aplicação (`app/`)
| Arquivo | Status | Conteúdo |
|---|---|---|
| `config.py` | ✅ | Configurações via `pydantic-settings` (lê `.env`) |
| `db/models.py` | ✅ | Tabelas `products`, `inventory`, `orders`, `order_items` (SQLAlchemy 2.0) |
| `db/session.py` | ✅ | Engine e sessão |
| `db/queries.py` | ✅ | `total_revenue`, `top_products`, `daily_sales`, `inventory_status`, `search_products` |
| `tools/sales.py` | ✅ | `get_sales` (métricas: summary, top_products, daily) |
| `tools/inventory.py` | ✅ | `get_inventory` (com filtro de estoque baixo) |
| `tools/menu.py` | ✅ | `search_menu` (por texto ou categoria) |
| `tools/promotion.py` | ✅ | `create_promotion` — só **sugere** itens com estoque ≥ 2× o mínimo e venda baixa nos últimos 7 dias |
| `tools/registry.py` | ✅ | Registro central das tools com JSON Schema (para o LLM) |
| `schemas.py` | ✅ | `ChatRequest`, `ChatResponse`, `ToolCallRecord`, `Source` |
| `main.py` | ✅ | FastAPI: `GET /health`, `GET /tools`, `POST /chat` (retorna 501 até o agente existir) |
| `agent/prompts.py` | ✅ | System prompt com as regras de confiabilidade |
| `agent/graph.py` | ⏳ stub | `run_agent()` — Fase 2 |
| `rag/ingest.py` | ⏳ parcial | `chunk_text()` pronto; `ingest()` — Fase 3 |
| `rag/retriever.py` | ⏳ stub | `retrieve()` — Fase 3 |

### Dados (`data/`)
- `seed.py` — gera dados sintéticos **determinísticos** (seed 42): 20 produtos em 7 categorias, ~60 pedidos/dia com variação por dia da semana e horário de pico.
  - Estoque baixo proposital: Bacon Burger, Orange Juice, Cheesecake.
  - Excesso de estoque proposital: Greek Salad, Sweet Potato Fries, Club Sandwich.
  - Isso garante respostas conhecidas para a avaliação.
- `docs/promotion_policy.md` e `docs/inventory_procedures.md` — documentos para o RAG.

### Avaliação (`eval/`)
- `dataset.jsonl` — 6 perguntas de exemplo (uma de cada tipo do README). Meta: 50+.
- `metrics.py` — tool selection accuracy, F1, Recall@K, answer contains.
- `run_eval.py` — roda o benchmark contra o agente (depende da Fase 2).

### Testes (`tests/`)
- `conftest.py` — banco SQLite em memória com 30 dias de seed.
- `test_tools.py` — 7 testes das tools, registry e dataset.

## ⚠️ Pendências imediatas

1. ~~Instalar as dependências~~ ✅ feito.
2. ~~Rodar os testes~~ ✅ 7/7 passando (`.venv/bin/pytest -q`). O teste de promoção foi ajustado para checar a regra (cobertura ≥ 2×, sem itens de estoque baixo) em vez de exigir só itens de `OVERSTOCK`.
3. **Docker não está instalado** na máquina. Para usar Postgres: instalar Docker e rodar `docker compose up -d db`, depois `python -m data.seed --reset`.
4. Fazer o primeiro commit.

## 🔜 Próximos passos

### Fase 1 — terminar
- [ ] Resolver as pendências acima.
- [ ] Validar o seed no Postgres e conferir os números com algumas queries manuais.

### Fase 2 — Agente
- [ ] Escolher o provedor de LLM e preencher `.env`.
- [ ] Implementar `run_agent()` em `app/agent/graph.py` com LangGraph: LLM → tool calls → validação com o `input_model` → execução → repetir até a resposta final.
- [ ] Registrar cada chamada em `ToolCallRecord` (inclusive falhas).
- [ ] Tratar erros: argumentos inválidos, tool que falha, pedido fora do escopo.

### Fase 3 — RAG
- [ ] Escrever mais 5–8 documentos em `data/docs/`.
- [ ] Implementar `ingest()` (embeddings + ChromaDB) e `retrieve()`.
- [ ] Criar a tool `retrieve_documents` no registry.
- [ ] Preencher `sources` na resposta (banco vs. documento).

### Fase 4 — Avaliação
- [ ] Expandir `eval/dataset.jsonl` para 50+ perguntas.
- [ ] Adicionar faithfulness, hallucination rate, latência e tokens ao `run_eval.py`.
- [ ] Salvar resultados em `eval/results/` e analisar as falhas.

### Fase 5 — Produção
- [ ] Logs estruturados, Docker completo, interface demo (ex.: Streamlit).
