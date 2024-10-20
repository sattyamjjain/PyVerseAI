from transformers import (
    pipeline,
    BertForTokenClassification,
    BertTokenizer,
    RobertaForTokenClassification,
    RobertaTokenizer,
)

# Load BERT model and tokenizer
bert_model = BertForTokenClassification.from_pretrained(
    "dbmdz/bert-large-cased-finetuned-conll03-english"
)
bert_tokenizer = BertTokenizer.from_pretrained(
    "dbmdz/bert-large-cased-finetuned-conll03-english"
)

# Load RoBERTa model and tokenizer
roberta_model = RobertaForTokenClassification.from_pretrained("roberta-large-mnli")
roberta_tokenizer = RobertaTokenizer.from_pretrained("roberta-large-mnli")

# Initialize NER pipelines
bert_ner_pipeline = pipeline("ner", model=bert_model, tokenizer=bert_tokenizer)
roberta_ner_pipeline = pipeline("ner", model=roberta_model, tokenizer=roberta_tokenizer)


def ensemble_entity_extraction(text):
    """
    Perform entity extraction using an ensemble of BERT and RoBERTa models.
    The ensemble merges the outputs and considers the highest confidence score for each entity.
    """
    # Extract entities with BERT
    bert_entities = bert_ner_pipeline(text)

    # Extract entities with RoBERTa
    roberta_entities = roberta_ner_pipeline(text)

    # Combine results from both models
    final_entities = []
    entity_dict = {}

    # Merge entities, considering overlaps and confidence scores
    for entity in bert_entities + roberta_entities:
        word = entity["word"]
        if word not in entity_dict:
            entity_dict[word] = entity
        else:
            # Combine confidence scores or use voting logic if the entity exists
            entity_dict[word]["score"] = max(
                entity_dict[word]["score"], entity["score"]
            )

    final_entities = list(entity_dict.values())
    return final_entities
