# Código do FoodOps AI, arquivo por arquivo

Explicação detalhada de cada arquivo. A ordem segue as dependências: primeiro a base (configuração e banco), depois o que é construído em cima dela. Para os conceitos por trás de cada peça, veja [`CONCEITOS.md`](CONCEITOS.md).

---

# Parte 1: Configuração

## `app/config.py`

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
```
- `pydantic_settings` é uma biblioteca que lê configurações de **variáveis de ambiente** e de arquivos `.env`.
- `lru_cache` é um decorador que guarda o resultado de uma função na memória.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```
- Por herdar de `BaseSettings`, cada atributo da classe vira uma configuração que pode vir do ambiente.
- `env_file=".env"`: também lê o arquivo `.env`, se existir.
- `extra="ignore"`: se o `.env` tiver variáveis que a classe não conhece, ignora em vez de dar erro.

```python
    database_url: str = "postgresql+psycopg://foodops:foodops@localhost:5432/foodops"
    llm_model: str = ""
    llm_api_key: str = ""
    chroma_path: str = "./.chroma"
```
- Cada linha é uma configuração com um **valor padrão**.
- O nome do atributo vira o nome da variável de ambiente, sem diferenciar maiúsculas: `database_url` lê `DATABASE_URL`.
- A URL `postgresql+psycopg://usuario:senha@host:porta/banco` diz ao SQLAlchemy: "use Postgres, com o driver psycopg".

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```
- Cria o objeto `Settings` **uma vez só**. Nas chamadas seguintes, o `lru_cache` devolve o mesmo objeto, sem reler o `.env`.

---

# Parte 2: Banco de dados

## `app/db/models.py`: as tabelas

Este arquivo usa o **ORM** do SQLAlchemy: cada classe Python vira uma tabela, e cada objeto vira uma linha.

```python
class Base(DeclarativeBase):
    pass
```
- É a classe-mãe de todos os modelos. Ela guarda um "catálogo" de todas as tabelas em `Base.metadata`, que depois é usado para criar as tabelas de uma vez (`Base.metadata.create_all(engine)`).

### Tabela `products`

```python
class Product(Base):
    __tablename__ = "products"
```
- `__tablename__` é o nome da tabela no banco.

```python
    id: Mapped[int] = mapped_column(primary_key=True)
```
- `Mapped[int]` declara uma coluna inteira e **obrigatória** (NOT NULL), porque o tipo não é `int | None`.
- `primary_key=True`: é o identificador único. O banco gera automaticamente (1, 2, 3...).

```python
    name: Mapped[str] = mapped_column(String(100), unique=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(String(500))
```
- `String(100)` é um texto de até 100 caracteres.
- `unique=True`: dois produtos não podem ter o mesmo nome.
- `index=True`: cria um **índice**, que deixa rápidas as buscas por categoria.

```python
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
```
- `Numeric(10, 2)` é um número com até 10 dígitos, 2 deles depois da vírgula.
- Usa `Decimal` em vez de `float` porque `float` tem erro de arredondamento (`0.1 + 0.2 = 0.30000000000000004`). Com dinheiro isso não pode acontecer.

```python
    is_available: Mapped[bool] = mapped_column(default=True)
```
- Indica se o produto está disponível. O padrão é verdadeiro.

```python
    inventory: Mapped["Inventory"] = relationship(back_populates="product")
```
- **Não é uma coluna.** É um atalho do Python: `produto.inventory` devolve o objeto de estoque daquele produto, e o SQLAlchemy faz a consulta sozinho.
- `back_populates="product"` liga este atalho ao atalho do outro lado (`Inventory.product`), então os dois ficam sincronizados.

### Tabela `inventory`

```python
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), primary_key=True)
```
- `ForeignKey("products.id")` é uma **chave estrangeira**: este valor precisa existir na coluna `id` de `products`. O banco impede estoque de um produto que não existe.
- Também é `primary_key`, o que significa **um estoque por produto** (relação 1 para 1).

```python
    quantity: Mapped[int]
    min_quantity: Mapped[int]
```
- Sem `mapped_column(...)`, o SQLAlchemy cria uma coluna inteira simples e obrigatória.
- `quantity` é quanto existe. `min_quantity` é o nível mínimo: abaixo dele, é preciso repor.

```python
    unit: Mapped[str] = mapped_column(String(20), default="unit")
    updated_at: Mapped[datetime]
```
- `unit` é a unidade de medida ("unit", "kg"...). `updated_at` registra a última contagem.

### Tabela `orders`

```python
    created_at: Mapped[datetime] = mapped_column(index=True)
    channel: Mapped[str] = mapped_column(String(20))  # dine_in | takeaway | delivery
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
```
- `created_at` tem índice porque **toda** consulta de vendas filtra por data.
- `items` é um `list[...]`, porque um pedido tem **vários** itens (relação 1 para N).

### Tabela `order_items`

```python
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
```
- Cada linha diz "no pedido X, foram N unidades do produto Y, a R$ Z cada".
- O `unit_price` fica gravado aqui porque, se o preço do cardápio mudar amanhã, as vendas antigas continuam com o valor que foi realmente cobrado.

Resumo das relações:
```
products 1───1 inventory
products 1───N order_items N───1 orders
```

## `app/db/session.py`: a conexão

```python
engine = create_engine(get_settings().database_url)
```
- O **engine** é o objeto que sabe se conectar ao banco. Ele mantém um "pool" de conexões abertas para reutilizar.
- Ele é criado assim que o módulo é importado. `create_engine` **não conecta ainda**, só se prepara. A conexão acontece na primeira consulta.

```python
SessionLocal = sessionmaker(bind=engine)
```
- É uma "fábrica" de sessões. Uma **sessão** é uma conversa com o banco: você faz consultas e alterações, e no fim confirma (`commit`) ou descarta.

```python
def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
```
- É uma função **geradora** (por causa do `yield`). O FastAPI usa este padrão assim:
  1. Abre a sessão.
  2. Entrega a sessão para a rota (`yield`).
  3. Quando a rota termina, o código volta depois do `yield`, o `with` acaba e **a sessão é fechada automaticamente**.

## `app/db/queries.py`: as consultas

```python
_line_total = OrderItem.quantity * OrderItem.unit_price
```
- **Não calcula nada agora.** Cria uma *expressão SQL* que significa `quantity * unit_price`, o valor total de uma linha do pedido.
- É reutilizada em várias queries. O `_` no começo indica que é "interna" do arquivo.

### `total_revenue`

```python
def total_revenue(session: Session, start: datetime, end: datetime) -> dict:
    stmt = (
        select(func.coalesce(func.sum(_line_total), 0), func.count(func.distinct(Order.id)))
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= start, Order.created_at < end)
    )
```
Em SQL, isso equivale a:
```sql
SELECT COALESCE(SUM(quantity * unit_price), 0), COUNT(DISTINCT orders.id)
FROM order_items JOIN orders ON order_items.order_id = orders.id
WHERE orders.created_at >= :start AND orders.created_at < :end
```
- `func.sum(...)` soma o valor de todas as linhas, o que dá o faturamento.
- `func.coalesce(..., 0)`: se não houver vendas, `SUM` retorna `NULL`, e o `coalesce` troca por 0.
- `count(distinct(Order.id))` conta **pedidos**, não itens. Um pedido com 3 itens aparece 3 vezes no JOIN, e o `distinct` evita contar três vezes.
- `.join(...)` é necessário porque a data está em `orders`, mas os valores estão em `order_items`.
- `>= start` e `< end`: o intervalo é **meio-aberto**, inclui o início e exclui o fim. Isso evita contar a meia-noite em dois dias.

```python
    revenue, n_orders = session.execute(stmt).one()
    revenue = float(revenue)
```
- `.one()` pega a única linha do resultado e desempacota os dois valores.
- Converte para `float` porque o JSON não tem tipo `Decimal`.

```python
    return {
        "revenue": round(revenue, 2),
        "orders": n_orders,
        "average_order_value": round(revenue / n_orders, 2) if n_orders else 0.0,
    }
```
- Ticket médio = faturamento ÷ pedidos. O `if n_orders else 0.0` evita divisão por zero.

### `top_products`

```python
    units = func.sum(OrderItem.quantity).label("units")
```
- `.label("units")` dá um nome à coluna calculada (`AS units` em SQL), para poder ordenar por ela.

```python
    stmt = (
        select(Product.name, units, func.sum(_line_total).label("revenue"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.created_at >= start, Order.created_at < end)
        .group_by(Product.name)
        .order_by(units.desc())
        .limit(limit)
    )
```
- Dois JOINs: `products → order_items` (para saber o nome) e `order_items → orders` (para filtrar por data).
- `group_by(Product.name)` agrupa as linhas por produto, então `SUM` soma **por produto**.
- `order_by(units.desc())` ordena do mais vendido para o menos vendido.
- `.limit(limit)` pega só os N primeiros.

```python
    return [
        {"product": name, "units": int(u), "revenue": round(float(r), 2)}
        for name, u, r in session.execute(stmt)
    ]
```
- É uma *list comprehension*: para cada linha do resultado, monta um dicionário.

### `daily_sales`

```python
    day = func.date(Order.created_at).label("day")
```
- `DATE(created_at)` corta a hora: `2026-10-01 19:42` vira `2026-10-01`. Isso permite agrupar por dia.
- O resto segue o mesmo padrão: agrupa por dia, soma e ordena cronologicamente.

### `inventory_status`

```python
    stmt = select(Product.name, Inventory.quantity, Inventory.min_quantity, Inventory.unit).join(
        Inventory, Inventory.product_id == Product.id
    )
    if low_stock_only:
        stmt = stmt.where(Inventory.quantity <= Inventory.min_quantity)
```
- A query é montada **em partes**: o filtro só é adicionado se `low_stock_only=True`. Esta é uma vantagem do SQLAlchemy sobre escrever SQL em texto.

```python
    stmt = stmt.order_by(Inventory.quantity - Inventory.min_quantity)
```
- Ordena pela "folga" (quanto sobra acima do mínimo). Os mais críticos aparecem primeiro.

```python
            "low_stock": qty <= min_qty,
```
- Calcula no Python um campo booleano pronto para o LLM ler, sem ele precisar fazer a conta.

### `search_products`

```python
    stmt = select(Product)
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(or_(Product.name.ilike(pattern), Product.description.ilike(pattern)))
    if category:
        stmt = stmt.where(Product.category.ilike(category))
```
- `select(Product)` seleciona **objetos** `Product` inteiros, não colunas soltas.
- `%texto%` em SQL significa "contém texto em qualquer posição".
- `ilike` é um `LIKE` que ignora maiúsculas e minúsculas ("PIZZA" encontra "Pizza").
- `or_(...)`: o texto pode estar no nome **ou** na descrição. Buscar "bacon" encontra o Bacon Burger (pelo nome) e o Club Sandwich (pela descrição).
- Os dois filtros são opcionais e se combinam com E.

```python
        for p in session.scalars(stmt.order_by(Product.name))
```
- `session.scalars(...)` devolve diretamente os objetos `Product`, sem tuplas.

---

# Parte 3: Tools

Todas seguem o mesmo padrão: **uma classe de entrada (Pydantic) e uma função**.

## `app/tools/sales.py`

```python
class GetSalesInput(BaseModel):
    start_date: date = Field(description="First day of the period (inclusive).")
    end_date: date = Field(description="Last day of the period (inclusive).")
    metric: Literal["summary", "top_products", "daily"] = "summary"
    limit: int = Field(default=3, ge=1, le=50, description="Used by top_products.")
```
- `BaseModel` do Pydantic **valida** os dados. Se o LLM mandar `start_date="ontem"`, dá erro, porque precisa ser uma data.
- `Field(description=...)`: essa descrição vai para o JSON Schema, e **é o que o LLM lê** para entender cada parâmetro.
- `Literal[...]` só aceita esses 3 valores exatos.
- `ge=1, le=50` significa maior ou igual a 1 e menor ou igual a 50. Impede `limit=-5` ou `limit=1000000`.

```python
def get_sales(session: Session, params: GetSalesInput) -> dict:
    start = datetime.combine(params.start_date, time.min)
    end = datetime.combine(params.end_date + timedelta(days=1), time.min)
```
- Aqui é feita a conversão de **datas inclusivas** (como um humano pensa: "de 1 a 7") para o **intervalo meio-aberto** das queries.
- `time.min` é 00:00:00.
- Exemplo: de 1/10 a 7/10 vira `>= 01/10 00:00` e `< 08/10 00:00`, o que inclui o dia 7 inteiro.

```python
    if params.metric == "top_products":
        data = queries.top_products(session, start, end, params.limit)
    elif params.metric == "daily":
        data = queries.daily_sales(session, start, end)
    else:
        data = queries.total_revenue(session, start, end)
```
- Uma tool, três métricas. Isso deixa o LLM com menos tools para escolher.

```python
    return {"metric": params.metric, "period": [...], "data": data}
```
- Devolve também **o que foi perguntado** (métrica e período). Assim o LLM pode citar na resposta "no período de X a Y...", o que ajuda na rastreabilidade.

## `app/tools/inventory.py` e `app/tools/menu.py`

São o mesmo padrão, mais simples: validam a entrada e repassam para a query.
```python
class GetInventoryInput(BaseModel):
    low_stock_only: bool = Field(default=False, ...)
```
```python
class SearchMenuInput(BaseModel):
    query: str | None = Field(default=None, ...)
    category: str | None = Field(default=None, ...)
```
- `str | None` quer dizer que o parâmetro é opcional: pode ser texto ou nada.

Por que ter tools se elas só repassam para as queries? É **separação de responsabilidades** (princípio da seção 9 do README):
- **queries** sabem falar com o banco.
- **tools** definem o *contrato* com o LLM: nomes, validação e formato.

Se amanhã você trocar o banco, só mexe nas queries. Se mudar como o LLM chama, só mexe nas tools.

## `app/tools/promotion.py`

```python
class CreatePromotionInput(BaseModel):
    reference_date: date = Field(description="Sales are analysed over the 7 days before this date.")
    max_items: int = Field(default=3, ge=1, le=10)
```

```python
    end = datetime.combine(params.reference_date, time.min)
    start = end - timedelta(days=7)
```
- Define a janela de análise: os 7 dias **antes** da data de referência.

```python
    units_sold = {
        row["product"]: row["units"] for row in queries.top_products(session, start, end, limit=1000)
    }
```
- **Reaproveita** a query `top_products` com um limite alto, para pegar todos os produtos.
- Monta um dicionário `{"Classic Burger": 120, "Greek Salad": 8, ...}`.
- Um produto que **não vendeu nada** não aparece aqui (o JOIN não encontra vendas). Por isso, mais abaixo, o código usa `.get(..., 0)`.

```python
    stock = queries.inventory_status(session)
```
- Pega o estoque de todos os produtos.

```python
    for item in stock:
        if item["min_quantity"] == 0:
            continue
        coverage = item["quantity"] / item["min_quantity"]
```
- **Cobertura** = estoque ÷ mínimo. Cobertura 3 significa "tenho 3× o mínimo".
- O `continue` pula produtos com mínimo 0, para não dividir por zero.

```python
        sold = units_sold.get(item["product"], 0)
        if coverage >= 2:
            candidates.append({**item, "units_sold_last_7d": sold, "stock_coverage": round(coverage, 2)})
```
- **A regra**: só entra se tiver pelo menos o dobro do mínimo. Isso também exclui automaticamente os itens com estoque baixo.
- `{**item, ...}` copia todos os campos de `item` e acrescenta dois novos.

```python
    candidates.sort(key=lambda c: (c["units_sold_last_7d"], -c["stock_coverage"]))
```
- Ordena por **dois critérios**: primeiro o que vendeu **menos**. Em caso de empate, o que tem **mais** estoque (o sinal `-` inverte a ordem).
- A lógica de negócio é promover o que está parado e sobrando.

```python
    return {
        "status": "proposal",
        ...
        "candidates": candidates[: params.max_items],
    }
```
- `"status": "proposal"` deixa explícito que é **só uma sugestão**. O README pede que nada seja alterado no sistema real.
- `[: max_items]` pega só os N primeiros.

## `app/tools/registry.py`

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_model: type[BaseModel]
    fn: Callable[[Session, BaseModel], dict]
```
- `@dataclass` gera automaticamente o construtor (`__init__`) a partir dos atributos.
- `frozen=True` torna o objeto **imutável**, ninguém altera uma tool depois de criada.
- `input_model: type[BaseModel]` guarda a **classe** (por exemplo `GetSalesInput`), não uma instância.
- `fn: Callable[...]` guarda a **função** em si (por exemplo `get_sales`).

```python
    def json_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }
```
- `model_json_schema()` é do Pydantic: transforma a classe num JSON Schema. Por exemplo, `GetSalesInput` vira algo como:
  ```json
  {"type": "object",
   "properties": {"start_date": {"type": "string", "format": "date", "description": "..."}, ...},
   "required": ["start_date", "end_date"]}
  ```
- Esse é o formato que as APIs de LLM esperam para *tool calling*.

```python
TOOLS: dict[str, Tool] = {
    t.name: t
    for t in [
        Tool("get_sales", "Revenue, order count, ...", GetSalesInput, get_sales),
        ...
    ]
}
```
- Um dicionário `{"get_sales": Tool(...), ...}`.
- Quando o LLM disser "quero chamar `get_sales` com estes argumentos", o agente vai fazer:
  ```python
  tool = TOOLS["get_sales"]
  params = tool.input_model(**argumentos)   # valida
  resultado = tool.fn(session, params)      # executa
  ```
- A descrição de cada tool é **o que o LLM usa para decidir qual chamar**. Escrever boas descrições melhora a "tool selection accuracy" que vai ser medida na avaliação.

---

# Parte 4: API

## `app/schemas.py`: os formatos de entrada e saída

```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
```
- É o corpo do `POST /chat`: `{"message": "..."}`. `min_length=1` rejeita mensagem vazia.

```python
class ToolCallRecord(BaseModel):
    tool: str
    arguments: dict
    success: bool
    error: str | None = None
```
- É o registro de **cada** tool que o agente chamou: com quais argumentos, se deu certo e qual foi o erro.
- Serve a dois princípios do README: **observabilidade** (ver o que aconteceu) e **avaliação** (comparar as tools chamadas com as esperadas).

```python
class Source(BaseModel):
    kind: Literal["database", "document"]
    reference: str
```
- Indica a fonte de cada informação: o banco ou um documento. O README pede essa distinção na seção 5.

```python
class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[ToolCallRecord] = []
    sources: list[Source] = []
```
- É a **saída estruturada** do agente: em vez de só texto, vem a resposta, o que ele fez e de onde tirou.

## `app/main.py`

```python
app = FastAPI(title="FoodOps AI", version="0.1.0")
```
- Cria a aplicação. O título e a versão aparecem no `/docs`.

```python
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```
- O decorador `@app.get("/health")` liga a URL `GET /health` a esta função.
- Serve para checar se a API está viva. O Docker e serviços de monitoramento usam esse tipo de rota.

```python
@app.get("/tools")
def list_tools() -> list[dict]:
    return [tool.json_schema() for tool in TOOLS.values()]
```
- Mostra exatamente o que o LLM vai receber. É útil para depurar.

```python
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, session: Session = Depends(get_session)) -> ChatResponse:
```
- `request: ChatRequest`: o FastAPI lê o JSON do corpo e valida com o Pydantic. Se faltar `message`, devolve 422 automaticamente.
- `Depends(get_session)` é a **injeção de dependência**: o FastAPI chama `get_session()`, entrega a sessão aqui e fecha no final.
- `response_model=ChatResponse` garante que a resposta segue esse formato e documenta isso no `/docs`.

```python
    try:
        return run_agent(session, request.message)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
```
- Como o agente ainda não existe, `run_agent` lança `NotImplementedError`, e a API converte isso em **HTTP 501** ("Not Implemented") em vez de quebrar com erro 500.

---

# Parte 5: Agente e RAG (stubs)

## `app/agent/prompts.py`

```python
SYSTEM_PROMPT = """You are FoodOps AI, ...
Rules:
- Use tools to obtain any number, ... Never estimate data you could query.
- If a tool fails, say so. Never claim an operation succeeded when it did not.
- Cite whether each fact came from the database or from a document.
- Promotions are proposals only; ...
- If the request is ambiguous or the information is unavailable, ask or say so.
"""
```
- É a "instrução de sistema" que o LLM recebe antes de qualquer pergunta. Cada regra corresponde a um princípio do README:
  - não inventar números, para reduzir alucinação;
  - admitir quando algo falhou (seção 9, Reliability);
  - citar a fonte (seção 5);
  - não alterar o sistema (seção 4.4);
  - pedir esclarecimento ou dizer que não sabe (os casos "ambíguo" e "indisponível" do dataset).

## `app/agent/graph.py`

```python
def run_agent(session: Session, message: str) -> ChatResponse:
    raise NotImplementedError("Agent orchestration is implemented in Phase 2.")
```
- Só a assinatura. A docstring no topo descreve o loop que vai ser implementado:
  1. O LLM recebe a mensagem e os schemas das tools.
  2. Se ele pedir tools, o agente valida, executa e devolve o resultado.
  3. Repete até ele dar a resposta final.
  4. Monta o `ChatResponse`.

## `app/rag/ingest.py`

```python
DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs"
```
- `__file__` é o caminho deste arquivo (`.../app/rag/ingest.py`).
- `.parents[2]` sobe 2 pastas acima da pasta do arquivo, chegando na raiz do projeto.
- `/ "data" / "docs"`: o `pathlib` usa `/` para juntar caminhos.

```python
def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    if size <= overlap:
        raise ValueError("size must be greater than overlap")
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks
```
- Corta o texto em pedaços de 800 caracteres, cada um **repetindo os últimos 100 do anterior**:
  ```
  pedaço 1: [0 ...... 800]
  pedaço 2:       [700 ...... 1500]
  pedaço 3:             [1400 ...... 2200]
  ```
- A **sobreposição** existe para que uma frase cortada no meio apareça inteira em pelo menos um pedaço.
- A verificação inicial evita um loop infinito: se `overlap >= size`, o `start` nunca avançaria.

## `app/rag/retriever.py`
- É só a assinatura de `retrieve(query, k)`, que vai devolver os k pedaços mais parecidos com a pergunta.

---

# Parte 6: Dados

## `data/seed.py`

### As constantes

```python
PRODUCTS = [
    ("Classic Burger", "burgers", "Beef patty, ...", "32.90", 10),
    ...
]
```
- Cada tupla traz nome, categoria, descrição, preço (como texto, para virar `Decimal` sem erro) e **peso de popularidade**.
- O peso 10 do Classic Burger contra o 2 da Greek Salad faz o hambúrguer ser sorteado cerca de 5× mais.

```python
LOW_STOCK = {"Bacon Burger", "Orange Juice", "Cheesecake"}
OVERSTOCK = {"Greek Salad", "Sweet Potato Fries", "Club Sandwich"}
```
- São as situações **plantadas**. Os itens de `OVERSTOCK` também têm popularidade baixa, então são candidatos naturais a promoção.

```python
CHANNELS = [("dine_in", 5), ("takeaway", 2), ("delivery", 3)]
WEEKDAY_FACTOR = [0.8, 0.8, 0.9, 1.0, 1.3, 1.5, 1.2]  # Mon..Sun
HOURS = [(11, 1), (12, 4), (13, 3), (14, 1), (18, 1), (19, 3), (20, 4), (21, 2), (22, 1)]
```
- `CHANNELS`: 50% salão, 20% retirada, 30% delivery.
- `WEEKDAY_FACTOR`: multiplicador por dia da semana. O sábado (1.5) tem quase o dobro da segunda (0.8).
- `HOURS`: pares (hora, peso). Os picos ficam às 12h e às 20h.

### A função `_weighted`

```python
def _weighted(rng: random.Random, pairs):
    values, weights = zip(*pairs)
    return rng.choices(values, weights=weights, k=1)[0]
```
- `zip(*pairs)` "transpõe" a lista: `[(a,1),(b,2)]` vira `(a,b)` e `(1,2)`.
- `rng.choices` sorteia um valor respeitando os pesos.

### A função `seed`

```python
def seed(session, days=90, end=None, rng_seed=42):
    rng = random.Random(rng_seed)
```
- Cria um gerador aleatório **próprio**, com uma semente fixa. Mesma semente, mesma sequência de sorteios, mesmos dados. Esta é a chave da reprodutibilidade.

```python
    end = (end or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=days)
```
- `end or datetime.now()`: se não passaram uma data final, usa hoje.
- Zera a hora, para começar à meia-noite.
- **Atenção:** ao usar `datetime.now()`, os dados mudam de data conforme o dia em que você roda. Os testes passam uma data fixa, e por isso são estáveis.

```python
    products = [Product(name=n, category=c, ...) for n, c, d, p, _ in PRODUCTS]
    session.add_all(products)
    session.flush()
```
- Cria os objetos e os adiciona à sessão.
- `flush()` **envia** os INSERTs ao banco sem confirmar ainda. Isso é necessário porque **os `id` só existem depois que o banco os gera**, e a próxima etapa precisa deles.

```python
    weights = {p.id: w for p, (*_, w) in zip(products, PRODUCTS)}
```
- Junta cada produto com seu peso. `(*_, w)` pega só o último elemento da tupla.

```python
    for p in products:
        min_qty = 20
        if p.name in LOW_STOCK:
            qty = rng.randint(3, 15)       # abaixo do mínimo
        elif p.name in OVERSTOCK:
            qty = rng.randint(90, 140)     # 4.5× a 7× o mínimo
        else:
            qty = rng.randint(30, 80)      # normal
```
- O estoque é gerado de acordo com o grupo. O caso do Ice Cream vem daqui: um produto "normal" pode receber até 80 de estoque, o que dá cobertura de 4×, maior que 2×.

```python
    for offset in range(days):
        day = start + timedelta(days=offset)
        n_orders = int(rng.gauss(60, 8) * WEEKDAY_FACTOR[day.weekday()])
```
- Percorre cada dia.
- `rng.gauss(60, 8)` é um sorteio pela distribuição normal, com média 60 e desvio 8: a maioria dos dias fica entre 52 e 68 pedidos.
- Esse valor é multiplicado pelo fator do dia da semana. `day.weekday()` retorna 0 para segunda e 6 para domingo.

```python
        for _ in range(max(n_orders, 0)):
            created = day.replace(hour=_weighted(rng, HOURS), minute=rng.randint(0, 59))
            order = Order(created_at=created, channel=_weighted(rng, CHANNELS))
```
- `max(..., 0)` garante que, se o sorteio der negativo (muito raro), não quebra.
- Sorteia a hora (com peso), o minuto e o canal.

```python
            chosen: dict[int, OrderItem] = {}
            for _ in range(rng.randint(1, 4)):
                product = _weighted(rng, product_pairs)
                if product.id in chosen:
                    chosen[product.id].quantity += 1
                else:
                    chosen[product.id] = OrderItem(product_id=product.id, quantity=1, unit_price=product.price)
            order.items = list(chosen.values())
```
- Cada pedido tem de 1 a 4 sorteios de produto.
- Se o mesmo produto sair duas vezes, o código **aumenta a quantidade** em vez de criar duas linhas. É mais realista: "2× Cola" em vez de "Cola, Cola".
- `order.items = ...` usa o `relationship`: ao salvar o pedido, os itens são salvos junto, já com o `order_id` certo.

```python
    session.commit()
```
- Confirma tudo de uma vez. Se algo der erro antes daqui, nada é salvo.

### A função `main` (linha de comando)

```python
    from app.db.session import SessionLocal, engine
```
- O import fica **dentro** da função de propósito: os testes importam `seed` sem precisar criar a conexão com o Postgres.

```python
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", ...)
```
- `argparse` lê os argumentos de `python -m data.seed --days 30 --reset`.
- `action="store_true"`: se a flag aparece, o valor é `True`.

```python
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
```
- `--reset` **apaga** todas as tabelas. `create_all` cria as que não existem.

```python
        if session.query(Product).first() and not args.reset:
            raise SystemExit("Database already has data. Use --reset to recreate it.")
```
- Proteção: se já houver dados e você não pediu reset, para. Sem isso, rodar duas vezes daria erro de nome duplicado (o `unique=True`).

```python
if __name__ == "__main__":
    main()
```
- Só executa `main()` quando o arquivo é **rodado diretamente**, não quando é importado.

## `data/docs/*.md`
- São textos comuns que simulam documentos internos do restaurante: a política de promoções e os procedimentos de estoque.
- Eles têm regras que **não estão no banco**, como "desconto máximo de 30%". Só dá para respondê-las via RAG. É isso que torna interessante a pergunta "sugira uma promoção seguindo a política": ela exige banco **e** documento.

---

# Parte 7: Avaliação

## `eval/dataset.jsonl`

O formato é **JSON Lines**: um objeto JSON por linha.
```json
{"id": "single-001", "type": "single_tool", "question": "Which products are low on stock?",
 "expected_tools": ["get_inventory"],
 "expected_answer_contains": ["Bacon Burger", "Orange Juice", "Cheesecake"]}
```
- `type` é a categoria da pergunta (as 6 categorias do README).
- `expected_tools` diz quais tools o agente **deveria** chamar.
- `expected_answer_contains` diz o que a resposta **deveria** mencionar. Essas respostas são conhecidas graças ao seed determinístico.
- `expected_behavior` é usado nos casos sem tool: `"refuse"` (deve recusar "apagar pedidos") ou `"state_unavailable"` (deve dizer que não tem dados de funcionários).
- `rag-db-001` espera uma tool `retrieve_documents`, que **ainda não existe** e vai ser criada na Fase 3.

## `eval/metrics.py`

```python
def tool_selection_accuracy(expected, called) -> float:
    return float(set(expected) == set(called))
```
- Retorna 1.0 se o agente chamou **exatamente** as tools esperadas e 0.0 caso contrário. É um critério rígido.
- Usa `set` para ignorar a ordem e as repetições.

```python
def tool_selection_f1(expected, called) -> float:
    exp, got = set(expected), set(called)
    if not exp and not got:
        return 1.0
    tp = len(exp & got)
    if tp == 0:
        return 0.0
    precision, recall = tp / len(got), tp / len(exp)
    return 2 * precision * recall / (precision + recall)
```
- É uma versão com **nota parcial**:
  - `tp` (verdadeiros positivos): quantas tools certas foram chamadas.
  - **precision**: das tools que chamou, quantas estavam certas. Penaliza chamar tool desnecessária.
  - **recall**: das tools esperadas, quantas chamou. Penaliza esquecer uma tool.
  - **F1** é a média harmônica das duas.
- Exemplo: esperava `{sales, inventory}` e chamou `{sales}`. Precision = 1/1 = 1.0, recall = 1/2 = 0.5, F1 = 0.67.
- Se não esperava nenhuma tool e não chamou nenhuma, a nota é 1.0 (acertou ao recusar).

```python
def recall_at_k(relevant, retrieved, k) -> float:
    return len(set(relevant) & set(retrieved[:k])) / len(set(relevant))
```
- É para o RAG: dos documentos relevantes, quantos apareceram entre os k primeiros resultados.

```python
def answer_contains(answer, expected) -> float:
    lowered = answer.lower()
    return sum(e.lower() in lowered for e in expected) / len(expected)
```
- Calcula a fração dos termos esperados que aparecem na resposta, sem diferenciar maiúsculas.
- `sum(...)` de booleanos conta os `True`, porque `True` vale 1.

## `eval/run_eval.py`

```python
def load_dataset(path=DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
```
- Lê o arquivo, divide em linhas, pula as vazias e converte cada uma de JSON para dicionário.

```python
        for case in load_dataset():
            t0 = time.perf_counter()
            response = run_agent(session, case["question"])
            latency = time.perf_counter() - t0
```
- Para cada pergunta, mede quanto tempo o agente leva. `perf_counter` é o relógio mais preciso do Python.

```python
            called = [c.tool for c in response.tool_calls]
            results.append({
                "tool_accuracy": tool_selection_accuracy(case["expected_tools"], called),
                ...
            })
```
- Aqui o `ToolCallRecord` do `schemas.py` mostra sua utilidade: a avaliação lê quais tools o agente realmente chamou e compara com as esperadas.

```python
    print(f"tool_accuracy={sum(r['tool_accuracy'] for r in results) / n:.2%}")
```
- Imprime a média geral formatada como porcentagem (`:.2%` transforma 0.8333 em `83.33%`).

---

# Parte 8: Testes

## `tests/conftest.py`

O pytest carrega este arquivo **automaticamente**, e tudo que está nele fica disponível para os testes.

```python
SEED_END = datetime(2026, 10, 1)
```
- Data fixa. Os dados de teste são sempre de 01/09 a 30/09/2026, não importa em que dia você rode.

```python
@pytest.fixture(scope="session")
def session():
```
- Uma **fixture** é algo que o pytest prepara e entrega aos testes. Quando um teste tem um parâmetro chamado `session`, o pytest procura uma fixture com esse nome e passa o valor.
- `scope="session"` aqui é a **sessão do pytest**, que é outra coisa (é coincidência de nome com a sessão do banco). Significa que a fixture roda **uma vez só** para todos os testes, e não uma vez por teste. Gerar 30 dias de dados uma vez é muito mais rápido.

```python
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
```
- `:memory:` é um banco SQLite que existe **só na memória RAM**. Some quando o teste termina e não cria nenhum arquivo.
- Cria as 4 tabelas.

```python
    with Session(engine) as s:
        seed(s, days=30, end=SEED_END)
        yield s
```
- Popula com 30 dias de dados.
- `yield s` entrega a sessão para os testes. Depois que todos terminam, o `with` fecha a sessão.

## `tests/test_tools.py`

O pytest roda toda função que começa com `test_`. Cada `assert` é uma verificação: se for falso, o teste falha.

### `test_sales_summary`
```python
    result = get_sales(session, GetSalesInput(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30)))
    assert result["data"]["orders"] > 0
    assert result["data"]["revenue"] > 0
```
- Pede o resumo de setembro inteiro e verifica que vieram pedidos e faturamento.
- **O que ele pegaria**: um JOIN errado, um filtro de data invertido ou a conversão de datas inclusivas quebrada. Qualquer um desses casos resultaria em zero.

### `test_top_products_respects_limit`
```python
    data = get_sales(session, params)["data"]   # metric="top_products", limit=3
    assert len(data) == 3
    assert data[0]["units"] >= data[1]["units"] >= data[2]["units"]
```
- Verifica o `.limit()` e o `.order_by(desc)`.
- `a >= b >= c` é uma comparação encadeada do Python, equivale a `a >= b and b >= c`.

### `test_low_stock_matches_seed`
```python
    data = get_inventory(session, GetInventoryInput(low_stock_only=True))["data"]
    assert {row["product"] for row in data} == LOW_STOCK
```
- É o teste mais forte: compara com **exatamente** os 3 produtos plantados no seed.
- Usa `set` (`{...}`) para não depender da ordem.
- **O que ele pegaria**: o filtro usando `<` em vez de `<=`, ou um produto "normal" entrando por engano.

### `test_search_menu_by_category`
```python
    data = search_menu(session, SearchMenuInput(category="pizzas"))["data"]
    assert {row["product"] for row in data} == {"Margherita Pizza", "Pepperoni Pizza", "Four Cheese Pizza"}
```
- Verifica que o filtro de categoria traz todas as pizzas e nada além delas.

### `test_promotion_excludes_low_stock`
```python
    result = create_promotion(session, CreatePromotionInput(reference_date=date(2026, 10, 1)))
    names = {c["product"] for c in result["candidates"]}
    assert result["status"] == "proposal"
    assert names.isdisjoint(LOW_STOCK)
    assert all(c["stock_coverage"] >= 2 for c in result["candidates"])
    assert names & OVERSTOCK
```
Quatro verificações:
1. Está marcado como **proposta**, não como ação executada.
2. `isdisjoint` confirma que **nenhum** item de estoque baixo foi sugerido. Esta é a regra de segurança mais importante.
3. `all(...)` confirma que **todos** os candidatos têm cobertura de pelo menos 2×.
4. `names & OVERSTOCK` é a interseção dos conjuntos. Um conjunto vazio é "falso" em Python, então isso verifica que **pelo menos um** item de excesso proposital apareceu.

### `test_registry_schemas`
```python
    for tool in TOOLS.values():
        assert tool.json_schema()["input_schema"]["type"] == "object"
```
- Garante que todas as tools geram um schema no formato que os LLMs esperam.
- **O que ele pegaria**: alguém criar uma tool nova com um `input_model` errado.

### `test_dataset_loads`
```python
    cases = load_dataset()
    assert all({"id", "question", "expected_tools"} <= set(c) for c in cases)
```
- `set(c)` são as chaves do dicionário. `<=` entre conjuntos significa "está contido em".
- Verifica que toda pergunta do dataset tem pelo menos esses 3 campos.
- **O que ele pegaria**: uma linha mal formatada no `.jsonl` ou um campo esquecido.

---

# Parte 9: Infraestrutura

## `pyproject.toml`
- `[project]` define nome, versão, a versão mínima do Python (3.11) e as **dependências obrigatórias**.
- `[project.optional-dependencies]` são grupos instalados só quando pedidos: `pip install -e ".[dev]"` instala o grupo `dev`. LangGraph e ChromaDB estão separados porque são pesados e ainda não são usados.
- `[tool.setuptools.packages.find]` diz quais pastas são pacotes Python (`app`, `data`, `eval`).
- `[tool.pytest.ini_options]` diz ao pytest para procurar os testes em `tests/`.
- O `-e` do `pip install` significa *editable*: o pip aponta para a sua pasta em vez de copiar os arquivos, então suas edições valem na hora.

## `docker-compose.yml`
- **`db`**:
  - `image: postgres:16` usa a imagem oficial.
  - `environment` define o usuário, a senha e o nome do banco. São os mesmos valores da URL padrão do `config.py`.
  - `ports: "5432:5432"` expõe o banco na sua máquina.
  - `volumes: pgdata:...` faz os dados **sobreviverem** quando o container é desligado.
  - `healthcheck` roda `pg_isready` a cada 5s para saber quando o banco está pronto.
- **`app`**:
  - `build: .` constrói a imagem usando o `Dockerfile`.
  - O `DATABASE_URL` aqui usa `db` como host em vez de `localhost`: dentro da rede do Docker, os serviços se encontram pelo nome.
  - `depends_on: condition: service_healthy` só sobe a app **depois** que o banco passar no healthcheck.

## `Dockerfile`
```dockerfile
FROM python:3.12-slim              # imagem base: Linux mínimo com Python
WORKDIR /code                      # pasta de trabalho dentro do container
COPY pyproject.toml .              # copia os arquivos do projeto
COPY app ./app
...
RUN pip install --no-cache-dir .   # instala (sem cache, para a imagem ficar menor)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- `--host 0.0.0.0` é necessário porque, dentro do container, `localhost` não seria acessível de fora.

## `.env.example` e `.gitignore`
- `.env.example` é um **modelo**. Você copia para `.env` e preenche. O `.env` real fica fora do git (está no `.gitignore`) porque vai conter a chave da API do LLM.
- `.gitignore` também exclui o `.venv/`, os caches do Python e do pytest, o banco do Chroma e os arquivos `.db`.

## `__init__.py` (vazios)
- Marcam as pastas como **pacotes Python**, o que permite fazer `from app.db.models import ...`.

---

# O caminho completo de uma requisição (quando o agente existir)

```
1. POST /chat {"message": "o que está acabando?"}
2. main.py valida com ChatRequest e abre a sessão via get_session
3. run_agent manda a mensagem, o SYSTEM_PROMPT e os schemas do TOOLS para o LLM
4. O LLM responde: "chamar get_inventory com {low_stock_only: true}"
5. O agente valida com GetInventoryInput e executa get_inventory
6.   └→ queries.inventory_status → SELECT ... WHERE quantity <= min_quantity
7. O resultado volta ao LLM, que escreve a resposta
8. O agente monta o ChatResponse (answer + tool_calls + sources)
9. main.py devolve o JSON e fecha a sessão
```

Hoje funcionam os passos 2, 5 e 6, e os testes comprovam isso. Os passos 3, 4, 7 e 8 são a Fase 2.
