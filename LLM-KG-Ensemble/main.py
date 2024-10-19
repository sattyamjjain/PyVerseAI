import os
from src.knowledge_graph.neo4j_connection import Neo4jConnection
from src.entity_extraction.entity_extraction import extract_entities
from src.data_ingestion.world_bank_ingestion import fetch_world_bank_documents  # Import the data fetching function


# Define the main workflow function
def run_workflow():
    # Step 1: Check if the data file exists, if not, fetch the data
    data_file_path = "data/processed/world_bank_documents.csv"

    if not os.path.exists(data_file_path):
        print("Data file missing, fetching data from World Bank API...")
        fetch_and_save_data()  # Fetch data from World Bank API
    else:
        print(f"Data file {data_file_path} found.")

    # Step 2: Set up Neo4j connection
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "YourPasswordHere"

    conn = Neo4jConnection(uri, user, password)

    # Step 3: Ingest documents and create country nodes/relationships
    print("Ingesting documents into Neo4j...")
    conn.ingest_documents_from_csv(data_file_path)
    conn.create_country_nodes_from_documents(data_file_path)
    conn.create_document_country_relationships_from_csv(data_file_path)

    # Step 4: Extract entities from a sample or actual text
    print("Extracting entities from text...")
    sample_text = """
    The energy project in Pakistan focuses on renewable energy sources. 
    The infrastructure development project in Vietnam includes road construction.
    """

    # Replace sample text with actual document content if available
    extracted_entities = extract_entities(sample_text)

    # Step 5: Insert extracted entities into Neo4j
    print("Inserting extracted entities into Neo4j...")
    for entity in extracted_entities:
        conn.create_entity_node(entity['word'], entity['entity'])

    # Step 6: Close the Neo4j connection
    conn.close()
    print("Workflow completed successfully!")


# Function to fetch data from the World Bank API
def fetch_and_save_data():
    df = fetch_world_bank_documents()
    if df is not None:
        os.makedirs("data/processed", exist_ok=True)
        df.to_csv("data/processed/world_bank_documents.csv", index=False)
        print("Data fetched and saved to data/processed/world_bank_documents.csv")
    else:
        print("No data fetched.")


# Execute the workflow
if __name__ == "__main__":
    run_workflow()
