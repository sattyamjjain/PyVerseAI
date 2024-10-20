from src.entity_extraction.entity_extraction import extract_entities


def test_extract_entities():
    text = "The energy project in Pakistan focuses on renewable energy."
    entities = extract_entities(text)
    assert len(entities) > 0
    assert "word" in entities[0]
    assert "entity" in entities[0]
