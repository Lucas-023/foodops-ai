# FoodOps AI
### An Intelligent Agent for Restaurant Operations

**FoodOps AI** is an AI-powered restaurant operations assistant designed to transform natural language requests into actionable insights and operational decisions.

The system combines Large Language Models (LLMs), tool calling, Retrieval-Augmented Generation (RAG), and structured data analysis to assist restaurant managers with daily operational tasks.

Instead of functioning as a conventional chatbot, FoodOps AI acts as an intelligent agent capable of interacting with external tools, querying databases, retrieving relevant information, and generating evidence-based recommendations.

---

## 1. Motivation

Restaurant managers frequently need to make decisions based on information distributed across different systems, including sales records, inventory databases, product catalogs, and operational documentation.

Accessing and interpreting this information manually can be time-consuming.

FoodOps AI aims to simplify this process by providing a natural language interface through which users can interact with operational data.

For example:

> "What were our three best-selling products this week? Are any products running low on inventory? Suggest a promotion for tomorrow."

The system should independently determine which information is needed, execute the appropriate operations, and generate a response grounded in actual data.

---

## 2. Main Objectives

The project has five primary objectives:

1. **Intelligent Tool Usage:** Enable an LLM to identify and execute the appropriate tools based on user requests.
2. **Data Retrieval:** Integrate structured databases and document retrieval systems.
3. **Contextual Reasoning:** Combine information from multiple sources to produce useful recommendations.
4. **Reliability:** Minimize hallucinations through structured outputs, validation, and evidence-based responses.
5. **Evaluation:** Develop a reproducible framework to measure the performance and reliability of the agent.

---

## 3. System Architecture

The initial architecture consists of the following components:

```text
                       USER
                         |
                         v
                  FastAPI Backend
                         |
                         v
                   Agent Orchestrator
                         |
               +---------+---------+
               |                   |
               v                   v
          Tool Calling             RAG
               |                   |
       +-------+-------+            v
       |       |       |       Vector Database
       v       v       v            |
     Sales  Inventory Menu          |
       |       |       |            |
       +-------+-------+------------+
                         |
                         v
                 Context Integration
                         |
                         v
                  LLM Response
                         |
                         v
                  Structured Output
                         |
                         v
                       USER
```

### Core Components

| Component | Responsibility |
|---|---|
| FastAPI | Expose the application through an API |
| Agent Orchestrator | Manage the reasoning and execution workflow |
| LLM | Interpret requests and generate responses |
| Tool Calling | Execute operations using external functions |
| PostgreSQL | Store structured operational data |
| RAG | Retrieve relevant information from documents |
| Vector Database | Store and retrieve document embeddings |
| Evaluation Framework | Measure system performance |

---

## 4. Agent Tools

The agent will initially have access to four tools.

### 4.1 Sales Analytics

`get_sales()`

Retrieve sales information and calculate relevant business indicators.

Possible operations:
- Total revenue over a specified period.
- Best-selling products.
- Sales trends.
- Average order value.
- Product performance comparisons.

### 4.2 Inventory Management

`get_inventory()`

Retrieve inventory information and identify potential supply problems.

Possible operations:
- Current inventory levels.
- Low-stock products.
- Products requiring replenishment.
- Inventory status.

### 4.3 Product Search

`search_menu()`

Search the restaurant's product catalog.

Possible operations:
- Search products by name.
- Retrieve product descriptions.
- Identify product categories.
- Retrieve prices and availability.

### 4.4 Promotion Assistant

`create_promotion()`

Generate promotion proposals based on sales performance and inventory conditions.

The initial implementation should generate recommendations rather than directly modifying real operational systems.

---

## 5. Retrieval-Augmented Generation

The RAG component will provide access to unstructured operational information.

Potential document sources include:
- Restaurant operational policies.
- Product documentation.
- Promotion guidelines.
- Internal manuals.
- Inventory management procedures.

The initial retrieval pipeline:

```text
Documents
    |
    v
Document Processing
    |
    v
Chunking
    |
    v
Embedding Generation
    |
    v
Vector Database
    |
    v
Semantic Retrieval
    |
    v
Retrieved Context
    |
    v
LLM
```

The agent should distinguish between information retrieved from documents and information obtained through structured database queries.

---

## 6. Evaluation Framework

A central objective of this project is to evaluate the reliability of the resulting AI system.

Rather than evaluating only whether responses sound reasonable, we will measure whether the agent actually performs the correct operations.

### Initial Evaluation Metrics

| Metric | Description |
|---|---|
| Tool Selection Accuracy | Whether the correct tools are selected |
| Tool Execution Success | Percentage of successful tool executions |
| SQL Query Accuracy | Whether generated queries produce correct results |
| Answer Faithfulness | Whether responses are supported by retrieved information |
| Retrieval Recall@K | Whether relevant documents appear in the top K results |
| Hallucination Rate | Frequency of unsupported factual claims |
| Latency | Time required to generate a response |
| Token Consumption | Number of tokens used per interaction |

### Evaluation Dataset

Develop a benchmark containing at least 50 natural language requests.

The dataset should include:
- Simple requests requiring one tool.
- Requests requiring multiple tools.
- Questions requiring both RAG and database retrieval.
- Ambiguous requests.
- Requests involving unavailable information.
- Requests that should be rejected or require clarification.

Each example should have an expected result against which the agent can be evaluated.

---

## 7. Technology Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| Backend | FastAPI |
| Agent Framework | LangGraph |
| LLM Integration | Model API |
| Database | PostgreSQL |
| Vector Database | ChromaDB |
| Embeddings | Sentence Transformers / API embeddings |
| Data Processing | Pandas |
| Testing | Pytest |
| Containerization | Docker |
| Version Control | Git |

Technology choices may evolve as the project develops.

---

## 8. Development Roadmap

### Phase 1 — Foundation
- [ ] Define project structure.
- [ ] Configure Python environment.
- [ ] Implement FastAPI application.
- [ ] Configure PostgreSQL.
- [ ] Create synthetic restaurant datasets.
- [ ] Implement basic database queries.

### Phase 2 — Agent Development
- [ ] Integrate an LLM.
- [ ] Implement tool calling.
- [ ] Develop sales analytics tools.
- [ ] Develop inventory tools.
- [ ] Develop product search.
- [ ] Implement agent orchestration.
- [ ] Handle execution errors and invalid requests.

### Phase 3 — RAG Integration
- [ ] Implement document ingestion.
- [ ] Develop document chunking.
- [ ] Generate embeddings.
- [ ] Configure vector database.
- [ ] Implement semantic retrieval.
- [ ] Integrate retrieved context into agent execution.

### Phase 4 — Evaluation
- [ ] Create evaluation dataset.
- [ ] Implement automated evaluation.
- [ ] Measure tool selection accuracy.
- [ ] Measure answer faithfulness.
- [ ] Evaluate retrieval performance.
- [ ] Measure latency and token consumption.
- [ ] Analyze failure cases.

### Phase 5 — Production-Oriented Improvements
- [ ] Implement structured logging.
- [ ] Add automated tests.
- [ ] Implement Docker configuration.
- [ ] Add API documentation.
- [ ] Improve error handling.
- [ ] Build a demonstration interface.

---

## 9. Engineering Principles

The project will follow several engineering principles:

**Modularity:** Each component should have a clearly defined responsibility.

**Reproducibility:** Experiments and evaluations should be repeatable.

**Reliability:** The agent should never fabricate database results or claim to have executed an operation that failed.

**Observability:** Tool executions, latency, errors, and token consumption should be recorded.

**Testability:** Core components should be independently testable.

**Separation of Concerns:** Business logic, database access, LLM orchestration, and API interfaces should remain independent.

---

## 10. Expected Outcome

The final objective is to deliver a functional, modular, and evaluated AI agent capable of interpreting natural language requests, interacting with structured and unstructured data sources, executing tools, and generating reliable operational recommendations.

The project will emphasize not only LLM integration but also the engineering practices required to build dependable AI-powered applications.

---

**Author:** Lucas Barros Barcelos  
**Institution:** IMPA Tech  
**Field:** Mathematics of Technology and Innovation — Data Science  
**Interests:** Artificial Intelligence, Machine Learning, Deep Learning, and Reinforcement Learning.