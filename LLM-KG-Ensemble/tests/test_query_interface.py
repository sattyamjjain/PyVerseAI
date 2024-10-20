import os
from src.query_interface.query_interface import Neo4jQueryInterface


def test_queries(uri, user, password):
    query_interface = Neo4jQueryInterface(uri, user, password)

    # Test 1: Query Documents by Entity
    entity_name = "India"
    print(f"Testing query_documents_by_entity for '{entity_name}':")
    documents = query_interface.query_documents_by_entity(entity_name)
    for doc in documents:
        print(doc)

    # Test 2: Query Entities by Document Type
    document_type = "Report"
    print(f"\nTesting query_entities_by_document for '{document_type}':")
    entities = query_interface.query_entities_by_document(document_type)
    for entity in entities:
        print(entity)

    # Test 3: Query Documents by Multiple Entities
    entity_names = ["India", "Pakistan"]
    print(f"\nTesting query_documents_by_multiple_entities for {entity_names}:")
    documents = query_interface.query_documents_by_multiple_entities(entity_names)
    for doc in documents:
        print(doc)

    # Test 4: Query Documents by Time Range
    start_date = "2020-01-01"
    end_date = "2023-12-31"
    print(
        f"\nTesting query_documents_by_time_range between {start_date} and {end_date}:"
    )
    documents = query_interface.query_documents_by_time_range(start_date, end_date)
    for doc in documents:
        print(doc)

    # Test 5: Query Entity Frequency Analysis
    print("\nTesting query_entity_frequency:")
    entities = query_interface.query_entity_frequency()
    for entity in entities:
        print(f"{entity['entity']}: {entity['mention_count']} mentions")

    query_interface.close()


# Add this to main.py for testing
if __name__ == "__main__":
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    # Call the test function
    test_queries(uri, user, password)
