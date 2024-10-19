
# **LLM-KG-Ensemble**

This project integrates document ingestion, entity extraction using large language models (LLMs), and knowledge graph construction using Neo4j. The goal is to build a structured representation of knowledge extracted from documents and entities, linking them in a meaningful way.

---

## **Table of Contents**
- [Project Overview](#project-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [How to Run](#how-to-run)
- [Data Ingestion](#data-ingestion)
- [Entity Extraction](#entity-extraction)
- [Knowledge Graph Integration (Neo4j)](#knowledge-graph-integration-neo4j)
- [Verification](#verification)
- [Contributing](#contributing)

---

## **Project Overview**

The `LLM-KG-Ensemble` project fetches documents, extracts key entities using a pre-trained language model (NER), and ingests them into a knowledge graph (Neo4j). This structured approach allows for enhanced data querying and exploration of relationships between documents and extracted entities like countries, project types, etc.

---

## **Prerequisites**

Before you begin, ensure you have the following tools installed on your system:
- **Python 3.8+**
- **Docker** (for Neo4j)
- **Neo4j Database** (running locally or in Docker)
- **Pandas** (for data manipulation)
- **Transformers** (for entity extraction)
- **Neo4j Python Driver**

---

## **Installation**

1. **Clone the repository:**
   ```bash
   git clone https://github.com/sattyamjjain/PyVerseAI.git
   cd LLM-KG-Ensemble
   ```

2. **Set up a Python virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Neo4j using Docker:**
   ```bash
   docker run -d --name neo4j      -p 7474:7474 -p 7687:7687      -e NEO4J_AUTH=neo4j/your_password      neo4j
   ```

---

## **Project Structure**

The following directory structure is used for the project:

```
.
├── data                  # Contains raw and processed data
│   ├── processed         # Processed data ready for ingestion
│   └── raw               # Raw data fetched or generated
├── docs                  # Documentation and design notes
├── models                # Models related to the project
│   ├── ensemble_models   # Ensemble models for various tasks
│   └── llm_models        # Pre-trained or fine-tuned LLM models
├── notebooks             # Jupyter notebooks for experimentation
├── src                   # Source code for data ingestion, extraction, and graph processing
│   ├── chatbot           # Chatbot integration (if applicable)
│   ├── data_ingestion    # Scripts for fetching and processing data
│   ├── ensemble          # Ensemble model logic
│   ├── entity_extraction # NER and entity extraction logic
│   ├── knowledge_graph   # Neo4j connection and graph creation logic
│   └── query_interface   # Interface for querying the knowledge graph
├── Dockerfile            # Docker configuration for the project
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation (this file)
```

---

## **How to Run**

### **Step 1: Set Up Data**
If you don't have any processed data, the script will fetch data automatically from the **World Bank API**:

1. Run the main project script:
   ```bash
   python3 main.py
   ```

This script will:
- Fetch documents from the **World Bank API** (if the data file is missing).
- Ingest the documents and relationships into **Neo4j**.
- Perform **Entity Extraction** using a pre-trained LLM and ingest entities into Neo4j.

### **Step 2: Access Neo4j**
After running the script, you can access Neo4j to visualize and query the data:
1. Open a browser and go to [http://localhost:7474](http://localhost:7474).
2. Log in with `neo4j/your_password`.

---

## **Data Ingestion**

If the data file `data/processed/world_bank_documents.csv` does not exist, the project will fetch data from the **World Bank API** and save it. The fetched data includes:
- `document_date`: The date of the document.
- `document_type`: Type of the document (e.g., Report, Project Appraisal Document).
- `country`: Country associated with the document.

---

## **Entity Extraction**

The project uses Hugging Face's `transformers` library for **Named Entity Recognition (NER)**. The pre-trained model extracts entities like locations, organizations, and more from the document text. These entities are ingested into Neo4j as `Entity` nodes.

---

## **Knowledge Graph Integration (Neo4j)**

- **Document Nodes**: The `Document` nodes are created in Neo4j with properties like `document_date`, `document_type`, and `country`.
- **Country Nodes**: Each document is linked to a `Country` node via a `BELONGS_TO` relationship.
- **Entity Nodes**: Extracted entities from the text (e.g., organizations, locations) are added as `Entity` nodes and linked to documents.

---

## **Verification**

1. **Check Data File**:
   - Ensure `data/processed/world_bank_documents.csv` exists.
   - Open it to verify the data format.

2. **Neo4j Verification**:
   - Open Neo4j in a browser: [http://localhost:7474](http://localhost:7474).
   - Run the following queries to verify:
     - **Document Nodes**: 
       ```cypher
       MATCH (d:Document) RETURN d LIMIT 10;
       ```
     - **Country Nodes**:
       ```cypher
       MATCH (c:Country) RETURN c LIMIT 10;
       ```
     - **Relationships**:
       ```cypher
       MATCH (d:Document)-[:BELONGS_TO]->(c:Country) RETURN d, c LIMIT 10;
       ```
     - **Extracted Entities**:
       ```cypher
       MATCH (e:Entity) RETURN e LIMIT 10;
       ```

---

## **Contributing**

If you would like to contribute to this project, feel free to open an issue or submit a pull request.