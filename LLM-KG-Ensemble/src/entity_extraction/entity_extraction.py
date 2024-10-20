from src.entity_extraction.ensemble_extraction import ensemble_entity_extraction


def extract_entities(text):
    """
    Extract named entities from the input text using an ensemble of BERT and RoBERTa models.
    """
    entities = ensemble_entity_extraction(text)
    return entities
