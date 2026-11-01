# Conceitos do FoodOps AI

Explicação conceitual de cada peça do projeto: **qual problema ela resolve**, **o que ela é** e **onde aparece no projeto**. Para a explicação linha a linha do código, veja [`CODIGO.md`](CODIGO.md).

---

## 0. O quadro geral: o que estamos construindo?

Imagine o gerente de um restaurante. Durante o dia ele precisa saber coisas como:
- "O que mais vendeu essa semana?"
- "O que está acabando no estoque?"
- "Que promoção faço amanhã?"

Hoje ele teria que abrir o sistema de vendas, olhar a planilha de estoque, ler o manual de promoções e juntar tudo de cabeça.

A ideia do projeto é **contratar um assistente digital**. O gerente pergunta em português normal, e o assistente vai nos sistemas, busca as informações, junta tudo e responde com base em dados reais.

Esse assistente tem duas partes:
- **O "cérebro"**: um LLM (como o ChatGPT ou o Claude). Ele entende a pergunta e sabe escrever a resposta.
- **As "mãos"**: código Python que nós escrevemos. Ele consulta o banco de dados e os documentos.

O cérebro sozinho **não sabe nada sobre o seu restaurante**. As mãos sozinhas **não entendem português**. O projeto inteiro é sobre ligar os dois de um jeito confiável.

Quase tudo que criamos até agora são as **mãos** e a **infraestrutura** em volta delas. O cérebro entra na Fase 2.

---

## 1. Configuração (`config.py`, `.env`)

### O problema
O mesmo código precisa rodar em lugares diferentes:
- no seu notebook, com um banco SQLite;
- no Docker, com um Postgres;
- nos testes, com um banco temporário na memória;
- um dia num servidor de verdade.

Em cada lugar, o **endereço do banco** é diferente. Além disso, o projeto vai ter uma **chave secreta** da API do LLM, que funciona como uma senha: quem tiver a chave gasta o seu dinheiro.

Se você escrever o endereço e a chave **direto no código**:
- precisa editar o código toda vez que muda de lugar;
- a chave vai parar no GitHub, e qualquer pessoa vê.

### A solução
Separar **o código** (igual em todo lugar) das **configurações** (que mudam de lugar para lugar).

As configurações ficam em **variáveis de ambiente**. São valores que o sistema operacional guarda "do lado de fora" do programa, e que o programa lê quando começa. Funciona como um bilhete que você entrega ao funcionário no começo do turno: "hoje o estoque fica no depósito B".

O arquivo **`.env`** é só um jeito prático de escrever esses bilhetes num arquivo, em vez de digitar tudo no terminal. Ele **não vai para o git** (está no `.gitignore`), e é isso que protege os segredos. O `.env.example` é um modelo sem segredos, que mostra quais variáveis existem.

### No projeto
O `config.py` define **quais** configurações existem e quais são os **valores padrão**. Por isso, quando você roda:
```bash
DATABASE_URL=sqlite:///foodops.db python -m data.seed
```
o mesmo código passa a usar SQLite em vez de Postgres, **sem mudar nenhuma linha**.

O `@lru_cache` serve para ler as configurações **uma vez só**, quando o programa começa, em vez de reler o arquivo a cada uso.

---

## 2. Banco de dados

### O problema
O restaurante tem milhares de pedidos. Onde guardar?

- **Numa variável Python?** Some quando o programa fecha.
- **Num CSV ou Excel?** Funciona com pouca coisa, mas fica ruim rápido:
  - para achar "vendas da semana passada", é preciso ler o arquivo **inteiro**;
  - se dois programas escreverem ao mesmo tempo, o arquivo corrompe;
  - nada impede você de digitar "abc" na coluna de preço.

### O que é
Um **banco de dados** é um programa especializado em guardar dados de forma **organizada, segura e rápida de consultar**. Ele roda separado do seu código, e o seu código "conversa" com ele.

Ele resolve os problemas acima:
- **Busca rápida**, com índices.
- **Vários acessos ao mesmo tempo** sem corromper.
- **Regras**: preço tem que ser número, todo pedido precisa existir, nomes não se repetem.
- **Transações**: ou salva tudo, ou não salva nada.

Usamos dois bancos:
- **PostgreSQL**: um banco "de verdade", que roda como servidor. É o que se usa em produção.
- **SQLite**: um banco que é só um arquivo (ou só memória). É ótimo para testes e desenvolvimento rápido.

### Banco relacional: tabelas
Os dois são bancos **relacionais**: os dados ficam em **tabelas**, parecidas com planilhas.

```
products
┌────┬─────────────────┬──────────┬───────┐
│ id │ name            │ category │ price │
├────┼─────────────────┼──────────┼───────┤
│ 1  │ Classic Burger  │ burgers  │ 32.90 │
│ 2  │ Bacon Burger    │ burgers  │ 38.90 │
│ 14 │ Cola            │ drinks   │  7.90 │
└────┴─────────────────┴──────────┴───────┘
```
- Cada **linha** é um produto. Cada **coluna** é uma característica.
- A **chave primária** (`id`) é o "RG" de cada linha: um número único que nunca se repete.

### Por que 4 tabelas, e não uma só?
Você poderia pensar em uma planilha gigante assim:
```
pedido │ data       │ produto        │ categoria │ preço │ qtd │ estoque
1      │ 01/10 12h  │ Classic Burger │ burgers   │ 32.90 │ 1   │ 45
1      │ 01/10 12h  │ Cola           │ drinks    │  7.90 │ 2   │ 60
2      │ 01/10 12h  │ Classic Burger │ burgers   │ 32.90 │ 1   │ 45
```
Os problemas aparecem logo:
- "Classic Burger, burgers, 45" se **repete** em todo pedido. Se o estoque mudar, você precisa atualizar milhares de linhas.
- Um produto que **nunca vendeu** não aparece em lugar nenhum.

A solução é **dividir por assunto**, um conceito chamado *normalização*. Cada informação vive em **um lugar só**:

| Tabela | Assunto | Analogia |
|---|---|---|
| `products` | o que o restaurante vende | o cardápio |
| `inventory` | quanto tem de cada coisa | a prateleira do depósito |
| `orders` | quando e como alguém comprou | a comanda |
| `order_items` | o que tinha em cada comanda | as linhas escritas na comanda |

As tabelas se ligam por **chaves estrangeiras**: `order_items.product_id = 1` significa "este item é o produto de id 1". É como escrever na comanda o **número** do prato em vez do nome inteiro.

**Por que o preço aparece em `order_items` e também em `products`?** Esta é a única repetição, e ela é proposital. `products.price` é o preço **de hoje**. `order_items.unit_price` é o preço **que o cliente pagou naquele dia**. Se o hambúrguer subir de preço amanhã, as vendas de ontem não podem mudar de valor.

### SQL
Para fazer perguntas ao banco, usamos uma linguagem chamada **SQL**:
```sql
SELECT name, price FROM products WHERE category = 'pizzas';
```
Lendo em voz alta: "selecione nome e preço da tabela de produtos onde a categoria é pizzas".

### Índice
Sem índice, para achar "pedidos de outubro" o banco lê **todos** os pedidos, um por um. Com um índice na coluna de data, ele mantém uma lista ordenada por data à parte, e vai direto ao ponto, como o índice remissivo no fim de um livro. Por isso colocamos `index=True` em `created_at`.

---

## 3. ORM: falar com o banco em Python (`models.py`)

### O problema
O banco fala SQL. Seu programa fala Python. Você poderia escrever SQL como texto dentro do Python:
```python
cursor.execute("SELECT * FROM products WHERE category = '" + categoria + "'")
```
Isso tem problemas sérios:
- É fácil errar a digitação, e o erro só aparece quando roda.
- É **perigoso**: se `categoria` vier de um usuário mal-intencionado, ele pode injetar comandos SQL (o ataque chamado *SQL injection*).
- Cada banco tem pequenas diferenças de SQL.

### O que é
Um **ORM** (Object-Relational Mapper) é um **tradutor** entre os dois mundos:
- uma **classe** Python corresponde a uma **tabela**;
- um **objeto** Python corresponde a uma **linha**;
- um **atributo** corresponde a uma **coluna**.

Usamos o **SQLAlchemy**, o ORM mais usado em Python. Você escreve:
```python
select(Product).where(Product.category == "pizzas")
```
e ele gera o SQL certo para Postgres ou SQLite, com proteção contra injection.

### No projeto
O `models.py` é a **planta** do banco. Ele descreve quais tabelas existem, quais colunas cada uma tem, quais são obrigatórias e como elas se ligam. A partir dessa planta, o SQLAlchemy cria as tabelas sozinho (`create_all`).

O `relationship` é uma conveniência: em vez de você fazer uma consulta para achar o estoque de um produto, escreve `produto.inventory` e o ORM busca por você.

---

## 4. Conexão e sessão (`session.py`)

### O que é
- O **engine** é a "linha telefônica" com o banco. Ele sabe o endereço e mantém algumas conexões abertas para reutilizar, porque abrir uma conexão nova é lento.
- A **sessão** é **uma ligação específica**: você abre, faz o que precisa (consultas, inserções) e desliga.

### Transações: "tudo ou nada"
Imagine que o seed está inserindo 5.000 pedidos e, no pedido 3.000, dá erro. Sem proteção, você fica com um banco **pela metade**, o que é pior que vazio.

A sessão agrupa tudo numa **transação**:
- As alterações ficam "pendentes".
- `commit()` **confirma tudo** de uma vez.
- Se der erro antes do commit, **nada** é salvo.

É o mesmo princípio de uma transferência bancária: o dinheiro não pode sair da sua conta sem entrar na outra.

### No projeto
O `get_session()` abre uma sessão para cada requisição da API e **garante que ela é fechada** no final, mesmo se der erro. Esquecer conexões abertas é um bug clássico que acaba derrubando o banco.

---

## 5. Queries: perguntas de negócio viram SQL (`queries.py`)

Cada função traduz **uma pergunta de negócio** em uma consulta. Há dois conceitos de SQL que aparecem o tempo todo.

### JOIN: juntar tabelas
A pergunta "qual o faturamento de outubro?" esbarra num problema: **a data está em `orders`**, mas **os valores estão em `order_items`**. O JOIN "cola" as linhas que se correspondem:

```
orders                    order_items
id │ created_at           order_id │ qty │ unit_price
1  │ 01/10                1        │ 1   │ 32.90
2  │ 02/10                1        │ 2   │  7.90
                          2        │ 1   │ 49.90

JOIN (order_items.order_id = orders.id):
created_at │ qty │ unit_price
01/10      │ 1   │ 32.90
01/10      │ 2   │  7.90
02/10      │ 1   │ 49.90
```
Agora dá para filtrar por data e somar `qty × unit_price`.

### GROUP BY: agrupar e resumir
A pergunta "quanto vendeu **cada** produto?" pede para separar as linhas em grupos (um por produto) e somar dentro de cada grupo:
```
Classic Burger: 1 + 1 + 3 + ...  = 412
Cola:           2 + 1 + 1 + ...  = 380
```
Depois é só ordenar do maior para o menor e pegar os 3 primeiros. Isso é o `top_products`.

### Por que devolver dicionários?
O resultado vai ser entregue ao LLM. O LLM lê **texto**, normalmente no formato **JSON**. Dicionários Python viram JSON diretamente.

---

## 6. API: a porta de entrada (`main.py`)

### O problema
O código está pronto, mas **como alguém usa?** O gerente não vai abrir o terminal e digitar Python. Ele vai usar um site, um app ou um chat. Esses programas precisam de uma forma padronizada de "pedir coisas" ao seu código.

### O que é
Uma **API** (Application Programming Interface) é um **cardápio de pedidos** que seu programa aceita.

Analogia: o **garçom**.
- O cliente (site, app) não entra na cozinha.
- Ele faz um **pedido** padronizado ao garçom ("um /tools, por favor").
- O garçom leva o pedido à cozinha (seu código) e volta com o **prato** (a resposta).

Na web, isso funciona via **HTTP**, o mesmo protocolo que o navegador usa:
- **URL / rota** (`/health`, `/chat`): *qual* pedido.
- **Método**: `GET` para "me dá informação"; `POST` para "toma estes dados e faça algo".
- **Corpo** (JSON): os detalhes do pedido, como `{"message": "o que está acabando?"}`.
- **Código de status**: o resultado. `200` deu certo; `422` seu pedido está mal formado; `500` a cozinha pegou fogo; `501` esse prato ainda não existe no cardápio.

### FastAPI
É o framework que usamos para criar a API. Ele cuida da parte chata: receber o HTTP, converter JSON, validar os dados e gerar documentação. Você escreve só a função.

Ele também gera o `/docs` sozinho: uma página onde você pode **testar a API pelo navegador**, sem escrever código.

### Servidor (uvicorn)
Um script normal roda e termina. Uma API precisa ficar **ligada esperando pedidos**, como um restaurante aberto. O **uvicorn** é o programa que mantém o restaurante aberto: ele fica escutando a porta 8000 e entrega cada pedido ao FastAPI.

---

## 7. Validação de dados (Pydantic, `schemas.py`)

### O problema
**Nunca confie em dados que vêm de fora.** Isso vale para usuários e vale **muito mais** para LLMs. Um LLM pode mandar:
- `start_date: "semana passada"` (não é uma data);
- `limit: 99999999`;
- um campo que não existe.

Se isso chegar no banco, o resultado pode ser erro, lentidão ou uma resposta errada que ninguém percebe.

### O que é
O **Pydantic** permite declarar **como os dados devem ser**:
```python
class GetSalesInput(BaseModel):
    start_date: date                 # tem que ser uma data
    limit: int = Field(ge=1, le=50)  # inteiro entre 1 e 50
```
Se o dado não seguir as regras, ele é **rejeitado na porta**, com uma mensagem clara do que estava errado. É o segurança na entrada.

Ele também faz uma segunda coisa importante: gera automaticamente uma **descrição** desse formato (o *JSON Schema*). É assim que o LLM fica sabendo quais parâmetros cada tool aceita.

---

## 8. LLM: o cérebro

### O que é
Um **LLM** (Large Language Model) é um modelo treinado em uma quantidade enorme de texto. Ele faz basicamente uma coisa: **dado um texto, prevê como ele continua**. Fazendo isso muito bem, ele consegue entender perguntas, raciocinar e escrever respostas.

### Por que ele sozinho não basta
Pergunte a um LLM "quais foram os mais vendidos do meu restaurante essa semana?":
- Ele **não tem acesso** ao seu banco. Nunca viu seus dados.
- Mesmo assim, como é treinado para continuar textos de forma plausível, ele pode **inventar** uma resposta convincente: "Os mais vendidos foram o X-Burger, a Coca e...". Isso se chama **alucinação**, e é o maior risco do projeto.

A solução é **dar ferramentas a ele**.

---

## 9. Tool calling: dar "mãos" ao cérebro (`tools/`, `registry.py`)

### A ideia central
Em vez de o LLM responder de cabeça, você diz a ele:

> "Você tem estas ferramentas disponíveis. Se precisar de dados, peça para usar uma."

**O ponto mais importante: o LLM não executa nada.** Ele só **escreve um pedido**. Quem executa é o **seu código**.

### Como é a conversa por baixo
```
SEU CÓDIGO → LLM:
   "Pergunta do gerente: o que está acabando no estoque?
    Ferramentas disponíveis:
      - get_inventory(low_stock_only: bool): estoque atual e itens em falta
      - get_sales(start_date, end_date, ...): vendas de um período
      ..."

LLM → SEU CÓDIGO:
   "Quero usar get_inventory com {low_stock_only: true}"

SEU CÓDIGO:
   (valida com Pydantic → executa a query no banco)

SEU CÓDIGO → LLM:
   "Resultado: [Bacon Burger: 8 unid (mín 20), Orange Juice: 5 (mín 20), Cheesecake: 12 (mín 20)]"

LLM → SEU CÓDIGO:
   "Três itens estão abaixo do mínimo: Bacon Burger (8), Orange Juice (5)..."
```
O LLM decide **o quê** buscar. O seu código **busca de verdade**. O LLM transforma o resultado em resposta. Assim ele não precisa inventar: **os números vêm do banco**.

### Por que isso importa para o projeto
- **Controle**: o LLM só consegue fazer o que as tools permitem. Não existe tool de "apagar pedido", então ele não tem como apagar.
- **Rastreabilidade**: dá para registrar exatamente quais tools ele chamou (o `ToolCallRecord`).
- **Avaliação**: dá para medir se ele escolheu as tools certas.

### No projeto
- Cada arquivo em `tools/` é uma ferramenta: o **formulário** de entrada (classe Pydantic) e a **ação** (função).
- O `registry.py` é o **catálogo de ferramentas** que vai ser mostrado ao LLM. A **descrição** de cada tool é crucial, porque é lendo essa descrição que o LLM decide qual usar.
- O `/tools` da API mostra exatamente esse catálogo.

---

## 10. Agente e orquestração (`agent/`)

### Chatbot × agente
- **Chatbot**: pergunta e resposta. Uma rodada só.
- **Agente**: recebe um **objetivo** e decide sozinho **quais passos** dar, em **loop**, até concluir.

A pergunta "quais os 3 mais vendidos, algum está acabando, e sugira uma promoção" exige vários passos:
```
1. LLM pensa: "preciso das vendas"            → chama get_sales
2. LLM pensa: "agora preciso do estoque"       → chama get_inventory
3. LLM pensa: "agora a política de promoção"   → busca nos documentos
4. LLM pensa: "tenho tudo"                     → escreve a resposta
```
O **orquestrador** é o código que roda esse loop: manda ao LLM, executa o que ele pedir, devolve o resultado, repete. Ele também cuida dos problemas: o que fazer se uma tool der erro, se o LLM pedir uma tool que não existe, ou se ele entrar em loop infinito.

O **LangGraph** é uma biblioteca que ajuda a montar esse loop como um **grafo**, um fluxograma com caixas ("chamar LLM", "executar tool") e setas ("se pediu tool, vai para executar; se terminou, vai para o fim").

O **system prompt** (`prompts.py`) é o "manual do funcionário" que o LLM recebe antes de tudo: "nunca invente números", "se algo falhar, diga", "cite a fonte"...

**Isto ainda não existe.** É a Fase 2.

---

## 11. RAG: ler documentos (`rag/`, `data/docs/`)

### O problema
Nem toda informação está em tabelas. A regra "desconto máximo de 30%" está num **documento de texto**. Não dá para fazer `SELECT` nela.

E se o restaurante tiver 200 páginas de manuais? Não dá para mandar tudo ao LLM a cada pergunta: seria caro, lento, e o LLM tem um limite de quanto texto consegue ler de uma vez.

### A solução: RAG (Retrieval-Augmented Generation)
"Geração aumentada por busca". O nome descreve o processo:
1. **Retrieval** (busca): achar **só os trechos relevantes** para a pergunta.
2. **Augmented** (aumentada): colar esses trechos na mensagem do LLM.
3. **Generation** (geração): o LLM responde usando os trechos.

### Como achar "trechos relevantes"?
Busca por palavra-chave falha fácil. A pergunta "quanto posso dar de desconto?" não contém a palavra "promoção", mas o trecho certo está no documento de promoções.

A solução são os **embeddings**: um modelo transforma cada texto numa **lista de números** (um vetor) que representa o **significado** do texto. Textos com significado parecido ficam com números parecidos, ou seja, **próximos** num espaço matemático.

```
"desconto máximo"         → [0.81, 0.12, -0.33, ...]  ┐ próximos
"limite de promoção"      → [0.79, 0.15, -0.30, ...]  ┘
"procedimento de limpeza" → [-0.20, 0.91, 0.44, ...]    longe
```
Para buscar:
1. Transforme a pergunta em vetor.
2. Encontre os vetores de trechos **mais próximos** dela.

O **banco vetorial** (ChromaDB) é um banco especializado em guardar esses vetores e achar os mais próximos rapidamente.

### Por que cortar em pedaços (chunking)?
Um documento inteiro fala de muitas coisas, e o vetor dele vira uma "média" sem foco. Pedaços menores têm significado mais específico, então a busca fica mais precisa. A **sobreposição** entre pedaços evita que uma frase importante seja cortada ao meio.

### No projeto
- `data/docs/` tem os documentos.
- `chunk_text` corta os documentos em pedaços (já está pronto).
- O resto (embeddings, ChromaDB, busca) é a Fase 3.

---

## 12. Dados sintéticos (`seed.py`)

### O problema
Você não tem um restaurante real com dados reais. E mesmo que tivesse, **não saberia de antemão as respostas certas** para testar o sistema.

### A solução
**Gerar dados falsos, mas realistas**, e **com situações plantadas**:
- Sabemos que o Bacon Burger está com estoque baixo, **porque nós colocamos isso lá**.
- Logo, se o agente disser que o estoque baixo é "Pizza Margherita", sabemos que ele errou.

É como um professor que monta a prova sabendo o gabarito.

### Determinismo (seed = 42)
Os dados são "aleatórios", mas com uma **semente fixa**. Um gerador aleatório com a mesma semente produz **sempre a mesma sequência**. Então rodar o seed hoje ou daqui a um mês gera **exatamente os mesmos dados**. Sem isso, o gabarito mudaria a cada execução.

O realismo (picos no almoço e no jantar, sábado mais cheio, hambúrguer vendendo mais que salada) existe para que as perguntas façam sentido e as respostas sejam interessantes.

---

## 13. Testes automatizados (`tests/`)

### O problema
Você muda uma linha no código. Será que quebrou alguma coisa em outro lugar? Testar à mão tudo de novo a cada mudança é impossível.

### O que é
**Testes automatizados** são código que **verifica** se o outro código funciona. Você escreve uma vez e roda quantas vezes quiser, em cerca de 1 segundo.

Cada teste segue o padrão:
1. **Prepara** a situação (banco com dados conhecidos).
2. **Executa** a função.
3. **Verifica** (`assert`) se o resultado é o esperado.

```python
resultado = get_inventory(low_stock_only=True)
assert resultado == {"Bacon Burger", "Orange Juice", "Cheesecake"}
```
Se alguém mudar a query e ela começar a trazer o produto errado, o teste **acusa na hora**.

### Fixture e banco na memória
- A **fixture** é a "preparação" compartilhada: criar o banco e preencher com dados uma vez, para todos os testes usarem.
- **SQLite na memória**: o banco existe só durante os testes e some depois. Assim os testes não dependem de você ter Postgres instalado e não sujam nenhum banco real.

### O caso do teste que falhou
Ele mostra para que testes servem. O teste de promoção falhou e nos fez perguntar: "o erro está no código ou no teste?". A resposta foi **no teste**, porque a expectativa estava errada (o Ice Cream merecia mesmo entrar na promoção). Às vezes o teste revela um bug no código; às vezes revela que você não tinha entendido direito a própria regra.

---

## 14. Avaliação (`eval/`): diferente de testes

### Por que não basta ter testes?
Testes funcionam para código **determinístico**: mesma entrada, mesma saída, sempre. `get_inventory` sempre devolve a mesma coisa.

O LLM **não é assim**:
- A mesma pergunta pode gerar respostas diferentes.
- Ele pode acertar 9 vezes e errar na 10ª.
- "Certo" às vezes é questão de grau. Chamou 2 das 3 tools necessárias: acertou ou errou?

Então, em vez de "passou ou falhou", medimos **taxas**: "o agente escolhe as tools certas em 87% das perguntas".

### Como funciona
1. Um **benchmark**: uma lista de perguntas, cada uma com o gabarito (quais tools deveria chamar e o que a resposta deveria conter). É o `dataset.jsonl`.
2. Rodar o agente em **todas** as perguntas.
3. Comparar com o gabarito usando **métricas**.

### As métricas, em linguagem simples
- **Tool selection accuracy**: chamou exatamente as ferramentas certas?
- **Precision**: das ferramentas que chamou, quantas eram necessárias? (Não chamou coisa à toa?)
- **Recall**: das ferramentas necessárias, quantas chamou? (Não esqueceu nenhuma?)
- **Recall@K**: na busca de documentos, o trecho certo apareceu entre os K primeiros?
- **Faithfulness / alucinação**: o que ele afirmou está mesmo nos dados que recebeu?
- **Latência e tokens**: quanto tempo e quanto dinheiro cada resposta custa.

### Por que isso é o "diferencial" do projeto
Qualquer pessoa consegue ligar um LLM a um banco e fazer uma demo bonita. Poucas conseguem **provar com números** que o sistema é confiável e mostrar **onde e por que** ele erra. Isso separa um protótipo de um sistema de engenharia, e é o que chama atenção num portfólio ou numa pesquisa.

---

## 15. Infraestrutura

### Ambiente virtual (`.venv`)
**O problema:** o projeto A precisa do pandas 2.0 e o projeto B do pandas 3.0. Se tudo for instalado "no computador", um quebra o outro.

**A solução:** cada projeto tem sua **própria caixinha** de pacotes, o `.venv`. Por isso os comandos usam `.venv/bin/pip` e `.venv/bin/pytest`: é o pip e o pytest **dessa caixinha**.

### `pyproject.toml`
É a "ficha técnica" do projeto: nome, versão e **lista de dependências**. Assim qualquer pessoa instala tudo com um comando, sem você ter que dizer quais pacotes usar. Os grupos opcionais (`dev`, `agent`, `rag`) permitem instalar só o necessário.

### Git e `.gitignore`
O git guarda o histórico do código. O `.gitignore` lista o que **não** deve ir para o histórico: segredos (`.env`), a caixinha de pacotes (`.venv`, que é enorme e cada um recria a sua) e arquivos temporários.

---

## 16. Docker

### O problema: "na minha máquina funciona"
Para rodar o FoodOps AI, uma pessoa precisa de:
- Python na versão certa;
- todos os pacotes nas versões certas;
- um PostgreSQL instalado, configurado, com usuário e senha certos, rodando na porta certa.

Se você mandar o projeto para um colega:
- ele tem Python 3.9 e o projeto precisa de 3.11 ou mais;
- ele usa Windows e algum pacote se comporta diferente;
- ele nunca instalou Postgres, e instalar e configurar leva uma tarde;
- ele já tem **outro** Postgres instalado, em outra versão, para outro projeto.

O resultado é que cada pessoa gasta horas montando o ambiente, e mesmo assim às vezes algo funciona para você e não para ela.

### A ideia: mandar a cozinha inteira, não só a receita
Pense na diferença entre:
- mandar **uma receita** para alguém: ela precisa ter os ingredientes, as panelas, o fogão certo...
- mandar **um food truck pronto**: cozinha, ingredientes, fogão, tudo dentro. Basta estacionar e ligar.

O Docker é o food truck. Ele empacota **o programa junto com tudo de que ele precisa para rodar** numa caixa padronizada, chamada **container**. Essa caixa roda igual em qualquer computador que tenha Docker.

O nome vem da analogia com **contêineres de navio**: antes deles, cada carga tinha um formato diferente e carregar um navio era um caos. Com uma caixa de tamanho padrão, qualquer navio, guindaste ou caminhão sabe lidar com qualquer carga, não importa o que tem dentro.

### Os conceitos

**Imagem**: o "molde" ou a "foto congelada" de um ambiente completo: um Linux mínimo, Python instalado, os pacotes do projeto e o seu código. A imagem não roda, ela é só o pacote pronto.
- Existem imagens prontas no **Docker Hub**, uma espécie de "loja de imagens". `postgres:16` é uma imagem oficial com o Postgres versão 16 já instalado e configurado. `python:3.12-slim` é uma imagem com um Linux mínimo e Python 3.12.

**Container**: uma imagem **rodando**. A relação é como entre uma **receita** e o **bolo**, ou, em programação, entre uma **classe** e um **objeto**: de uma imagem você pode criar vários containers.

**Dockerfile**: a **receita** para construir a sua própria imagem, passo a passo:
```dockerfile
FROM python:3.12-slim              # comece de uma imagem que já tem Python
WORKDIR /code                      # trabalhe dentro da pasta /code
COPY pyproject.toml .              # copie a lista de dependências
COPY app ./app                     # copie o código
RUN pip install --no-cache-dir .   # instale tudo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]  # ao ligar, rode a API
```
Cada linha é uma camada. O Docker guarda as camadas em cache: se você muda só o código, ele não reinstala o Python do zero.

**docker-compose.yml**: um projeto real normalmente tem **vários** containers que trabalham juntos. No nosso caso são dois, o banco e a API. O compose descreve esse conjunto e liga tudo com **um comando**:
```yaml
services:
  db:                        # container 1: o banco
    image: postgres:16       # usa a imagem pronta
    environment: ...         # usuário, senha, nome do banco
    ports: ["5432:5432"]     # expõe a porta para o seu computador
    volumes: [pgdata:...]    # guarda os dados fora do container
    healthcheck: ...         # como saber se o banco já está pronto
  app:                       # container 2: a API
    build: .                 # constrói usando o Dockerfile
    depends_on: db (healthy) # só liga depois do banco estar pronto
```

### Como funciona por dentro (sem entrar demais na parte técnica)
Um container **não é uma máquina virtual**, embora pareça.

- Uma **máquina virtual** simula um computador inteiro, com um sistema operacional completo dentro. É pesada: gigabytes de tamanho e minutos para ligar.
- Um **container** usa o **mesmo núcleo (kernel) do Linux** do seu computador, mas o processo fica **isolado**. Ele tem seus próprios arquivos, rede e processos, e "acha" que está sozinho na máquina. É leve: megabytes e segundos para ligar.

```
MÁQUINA VIRTUAL                       CONTAINER
┌──────────┐ ┌──────────┐             ┌──────────┐ ┌──────────┐
│   App    │ │   App    │             │   App    │ │   App    │
│ Python   │ │ Postgres │             │ Python   │ │ Postgres │
│ SO inteiro│ │ SO inteiro│            └──────────┘ └──────────┘
└──────────┘ └──────────┘             ┌──────────────────────────┐
┌──────────────────────────┐          │   Docker (isolamento)    │
│   Simulador de hardware  │          ├──────────────────────────┤
├──────────────────────────┤          │   Seu Linux (kernel)     │
│        Seu sistema       │          └──────────────────────────┘
└──────────────────────────┘
```

O isolamento traz algumas consequências práticas:
- **Rede própria**: dentro do compose, os containers se enxergam **pelo nome do serviço**. Por isso, dentro do container da API, o endereço do banco é `db:5432`, e não `localhost:5432`. O `localhost` de um container é ele mesmo.
- **Portas**: por padrão, nada de fora entra no container. O `ports: "5432:5432"` abre uma "janela": a porta 5432 do seu computador passa a apontar para a 5432 do container.
- **Arquivos descartáveis**: quando um container é apagado, tudo que estava dentro dele some. Para um banco de dados isso seria um desastre, então usamos um **volume** (`pgdata`): uma pasta que fica **fora** do container e sobrevive a ele.
- **`--host 0.0.0.0`**: por padrão o uvicorn só aceita conexões vindas "de dentro" do próprio container. O `0.0.0.0` diz "aceite de qualquer lugar", senão você não conseguiria acessar a API do seu navegador.

### Para que serve no FoodOps AI
1. **Postgres sem instalar Postgres**: `docker compose up -d db` e você tem um banco funcionando em segundos. Se estragar, apaga e cria de novo. Não interfere em nada mais no seu computador.
2. **Reprodutibilidade**: quem for avaliar o seu projeto roda `docker compose up` e tem **exatamente** o mesmo ambiente que você. Esse é um dos princípios do README.
3. **Caminho para produção**: servidores na nuvem rodam containers. A mesma imagem que você testou localmente é a que vai para o servidor.

### Comandos do dia a dia
```bash
docker compose up -d db       # liga só o banco, em segundo plano (-d = detached)
docker compose up --build     # constrói a imagem da API e liga tudo
docker compose ps             # mostra o que está rodando
docker compose logs app       # mostra o que a API escreveu (erros, prints)
docker compose down           # desliga tudo (os dados do volume continuam)
docker compose down -v        # desliga e APAGA os dados do volume
```

### Situação atual
O Docker **não está instalado** nesta máquina. Por isso usamos SQLite nos testes e no desenvolvimento. Os arquivos `Dockerfile` e `docker-compose.yml` já estão prontos para quando você instalar.

---

## Mapa: conceito → arquivo

```
CONCEITO                         ARQUIVO                         STATUS
────────────────────────────────────────────────────────────────────────
Configuração / segredos          config.py, .env.example         ✅
Estrutura do banco (tabelas)     db/models.py                    ✅
Conexão e transações             db/session.py                   ✅
Perguntas de negócio → SQL       db/queries.py                   ✅
Ferramentas do agente            tools/*.py                      ✅
Catálogo de ferramentas          tools/registry.py               ✅
Validação de dados               schemas.py + classes Input      ✅
Porta de entrada (API)           main.py                         ✅ (sem /chat)
Manual do LLM                    agent/prompts.py                ✅
Loop do agente                   agent/graph.py                  ⏳ Fase 2
Busca em documentos (RAG)        rag/*.py                        ⏳ Fase 3
Dados falsos com gabarito        data/seed.py                    ✅
Testes do código                 tests/                          ✅
Medição do agente                eval/                           ⏳ Fase 4
Ambiente reproduzível            pyproject, Dockerfile, compose  ✅
```

### A frase que resume tudo
Estamos construindo **as mãos** (tools que consultam dados reais) e **o controle de qualidade** (testes e avaliação) **antes** de colocar o cérebro (LLM). Quando o LLM entrar, ele já vai encontrar ferramentas confiáveis e uma forma de medir se ele as usa direito.
