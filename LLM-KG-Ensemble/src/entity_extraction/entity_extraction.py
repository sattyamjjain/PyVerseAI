from transformers import BertForTokenClassification, BertTokenizer, pipeline

# Load model and tokenizer
model = BertForTokenClassification.from_pretrained(
    "dbmdz/bert-large-cased-finetuned-conll03-english",
    ignore_mismatched_sizes=True,  # This will suppress the weight mismatch warning
)
tokenizer = BertTokenizer.from_pretrained(
    "dbmdz/bert-large-cased-finetuned-conll03-english"
)

# Initialize NER pipeline with model and tokenizer
ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer)


def extract_entities(text):
    """
    Extract named entities from the input text using a pre-trained BERT model.
    """
    entities = ner_pipeline(text)
    return entities
