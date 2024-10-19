from transformers import pipeline

# Load the pre-trained NER model
ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

def extract_entities(text):
    """
    Extract named entities from the input text using a pre-trained BERT model.
    """
    entities = ner_pipeline(text)
    return entities

if __name__ == "__main__":
    # Sample text for entity extraction
    text = """
    The energy project in Pakistan focuses on renewable energy sources. The infrastructure development project in Vietnam includes road construction.
    """

    # Perform entity extraction
    extracted_entities = extract_entities(text)

    # Display the extracted entities
    for entity in extracted_entities:
        print(f"Entity: {entity['word']}, Type: {entity['entity']}, Score: {entity['score']:.2f}")
