from neo4j import GraphDatabase


class Neo4jQueryInterface:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def query_documents_by_entity(self, entity_name):
        query = """
        MATCH (e:Entity {name: $entity_name})-[:MENTIONED_IN]->(d:Document)
        RETURN d.date AS document_date, d.type AS document_type, d.country AS country
        """
        with self.driver.session() as session:
            result = session.run(query, entity_name=entity_name)
            return [
                {
                    "document_date": record["document_date"],
                    "document_type": record["document_type"],
                    "country": record["country"],
                }
                for record in result
            ]

    def query_entities_by_document(self, document_type):
        query = """
        MATCH (d:Document {type: $document_type})<-[:MENTIONED_IN]-(e:Entity)
        RETURN e.name AS entity_name, e.type AS entity_type
        """
        with self.driver.session() as session:
            result = session.run(query, document_type=document_type)
            return [
                {
                    "entity_name": record["entity_name"],
                    "entity_type": record["entity_type"],
                }
                for record in result
            ]

    def query_documents_by_multiple_entities(self, entity_names):
        # Construct the MATCH clause dynamically to match all the entities
        match_clause = "MATCH " + ", ".join(
            [
                f"(e{i}:Entity {{name: $entity_name{i}}})-[:MENTIONED_IN]->(d:Document)"
                for i in range(len(entity_names))
            ]
        )

        query = f"""
        {match_clause}
        RETURN d.date AS document_date, d.type AS document_type, d.country AS country
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                **{
                    f"entity_name{i}": entity.strip()
                    for i, entity in enumerate(entity_names)
                },
            )
            return [record.data() for record in result]

    def query_documents_by_time_range(self, start_date, end_date, document_type=None):
        query = """
        MATCH (d:Document)
        WHERE d.date >= $start_date AND d.date <= $end_date
        """

        if document_type:
            query += " AND d.type = $document_type"

        query += " RETURN d.date AS document_date, d.type AS document_type, d.country AS country"

        with self.driver.session() as session:
            params = {"start_date": start_date, "end_date": end_date}
            if document_type:
                params["document_type"] = document_type
            result = session.run(query, **params)
            return [record.data() for record in result]

    def query_entity_frequency(self):
        query = """
        MATCH (e:Entity)-[:MENTIONED_IN]->(d:Document)
        RETURN e.name AS entity, COUNT(d) AS mention_count
        ORDER BY mention_count DESC
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [record.data() for record in result]
