import pandas as pd
from neo4j import GraphDatabase


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
            session.write_transaction(
                lambda tx: tx.run(
                    query,
                    document_date=document_date,
                    document_type=document_type,
                    country=country,
                )
            )

    def ingest_documents_from_csv(self, file_path):
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            try:
                document_date = row["document_date"]
                document_type = row["document_type"]
                country = row["country"]
            except KeyError as e:
                print(f"Missing column in row {index}: {e}")
                continue  # Skip rows with missing columns

            # Proceed with creating the document node
            self.create_document_node(document_date, document_type, country)

    def create_country_node(self, country):
        query = """
        MERGE (c:Country {name: $country})
        """
        with self.driver.session() as session:
            session.write_transaction(lambda tx: tx.run(query, country=country))

    def create_country_nodes_from_documents(self, file_path):
        df = pd.read_csv(file_path)
        countries = df["country"].unique()
        for country in countries:
            if pd.notna(country):  # Make sure the country is not null
                self.create_country_node(country)

    def create_document_country_relationship(self, document_type, country):
        query = """
        MATCH (d:Document {type: $document_type}), (c:Country {name: $country})
        MERGE (d)-[:BELONGS_TO]->(c)
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(query, document_type=document_type, country=country)
            )

    def create_document_country_relationships_from_csv(self, file_path):
        df = pd.read_csv(file_path)
        for index, row in df.iterrows():
            if pd.notna(
                row["country"]
            ):  # Only create relationships if country is not null
                self.create_document_country_relationship(
                    row["document_type"], row["country"]
                )

    # New method for creating organization nodes
    def create_organization_node(self, organization_name):
        query = """
        MERGE (o:Organization {name: $organization_name})
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(query, organization_name=organization_name)
            )

    def create_entity_node(self, entity, entity_type):
        query = """
        MERGE (e:Entity {name: $entity, type: $entity_type})
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(query, entity=entity, entity_type=entity_type)
            )

    # New method for creating award nodes
    def create_award_node(self, awardee, amount, city, state, zip_code, country):
        query = """
        CREATE (a:Award {awardee: $awardee, amount: $amount, city: $city, state: $state, zip: $zip_code, country: $country})
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(
                    query,
                    awardee=awardee,
                    amount=amount,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    country=country,
                )
            )

    def create_document_entity_relationship(self, document_type, entity_name):
        query = """
        MATCH (d:Document {type: $document_type}), (e:Entity {name: $entity_name})
        MERGE (e)-[:MENTIONED_IN]->(d)
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(
                    query, document_type=document_type, entity_name=entity_name
                )
            )

    # New Methods for Entity Relationships
    def create_entity_relationship(self, entity1, entity2, relationship):
        query = f"""
        MATCH (e1:Entity {{name: $entity1}}), (e2:Entity {{name: $entity2}})
        MERGE (e1)-[:{relationship}]->(e2)
        """
        with self.driver.session() as session:
            session.write_transaction(
                lambda tx: tx.run(query, entity1=entity1, entity2=entity2)
            )

    def create_collaboration_relationship(self, entity1, entity2):
        self.create_entity_relationship(entity1, entity2, "COLLABORATES_WITH")

    def create_working_relationship(self, entity1, entity2):
        self.create_entity_relationship(entity1, entity2, "WORKS_WITH")
