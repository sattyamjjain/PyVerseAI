import pandas as pd
from neo4j import GraphDatabase
from src.entity_extraction.entity_extraction import extract_entities

class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_document_node(self, document_date, document_type, country):
        query = """
        CREATE (d:Document {date: $document_date, type: $document_type, country: $country})
        """
        with self.driver.session() as session:
            try:
                session.write_transaction(
                    lambda tx: tx.run(query, document_date=document_date, document_type=document_type, country=country))
            except Exception as e:
                print(f"Error creating document node: {e}")

    def ingest_documents_from_csv(self, file_path):
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            self.create_document_node(row['document_date'], row['document_type'], row['country'])

    def create_country_node(self, country):
        query = """
        MERGE (c:Country {name: $country})
        """
        with self.driver.session() as session:
            try:
                session.write_transaction(lambda tx: tx.run(query, country=country))
            except Exception as e:
                print(f"Error creating country node: {e}")

    def create_country_nodes_from_documents(self, file_path):
        df = pd.read_csv(file_path)
        countries = df['country'].unique()
        for country in countries:
            if pd.notna(country):  # Make sure the country is not null
                self.create_country_node(country)

    def create_document_country_relationship(self, document_type, country):
        query = """
        MATCH (d:Document {type: $document_type}), (c:Country {name: $country})
        MERGE (d)-[:BELONGS_TO]->(c)
        """
        with self.driver.session() as session:
            try:
                session.write_transaction(lambda tx: tx.run(query, document_type=document_type, country=country))
            except Exception as e:
                print(f"Error creating document-country relationship: {e}")

    def create_document_country_relationships_from_csv(self, file_path):
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            if pd.notna(row['country']):  # Only create relationships if country is not null
                self.create_document_country_relationship(row['document_type'], row['country'])

    def create_entity_node(self, entity, entity_type):
        query = """
        MERGE (e:Entity {name: $entity, type: $entity_type})
        """
        with self.driver.session() as session:
            session.write_transaction(lambda tx: tx.run(query, entity=entity, entity_type=entity_type))


if __name__ == "__main__":
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "YourPasswordHere"

    conn = Neo4jConnection(uri, user, password)

    # Ingest documents and create country nodes and relationships
    conn.ingest_documents_from_csv("data/processed/world_bank_documents.csv")
    conn.create_country_nodes_from_documents("data/processed/world_bank_documents.csv")
    conn.create_document_country_relationships_from_csv("data/processed/world_bank_documents.csv")

    # Sample text for entity extraction
    sample_text = """
    The energy project in Pakistan focuses on renewable energy sources. 
    The infrastructure development project in Vietnam includes road construction.
    """

    # Extract entities from the sample text using the imported function
    extracted_entities = extract_entities(sample_text)

    # Insert extracted entities into Neo4j
    for entity in extracted_entities:
        conn.create_entity_node(entity['word'], entity['entity'])

    conn.close()