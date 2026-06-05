import spacy

print("Loading spaCy model...")
nlp = spacy.load("en_core_web_sm")

print("Processing text...")
doc = nlp("OpenAI builds AI systems.")

print("Entity extraction results:")
for ent in doc.ents:
    print(ent.text, ent.label_)
