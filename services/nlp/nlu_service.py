import spacy
import math

# Load the spaCy model
nlp = spacy.load("en_core_web_sm")

# Define 10 distinct intents with reference phrases for classification
INTENTS = {
    "greet": [
        "hello", "hi", "hey", "good morning", "good afternoon", "greetings",
        "howdy", "hello there", "hi there", "hey you"
    ],
    "goodbye": [
        "goodbye", "bye", "see you later", "exit", "quit", "stop", "terminate",
        "farewell", "bye bye", "quit application"
    ],
    "help": [
        "help", "info", "what can you do", "instructions", "how does this work",
        "give me help", "assist me", "show help", "get help"
    ],
    "transcribe_audio": [
        "transcribe", "speech to text", "convert audio", "transcribe audio",
        "convert speech to text", "transcription", "run speech to text",
        "transcribe this recording", "audio transcription"
    ],
    "synthesize_speech": [
        "synthesize", "text to speech", "generate audio", "read text",
        "generate speech", "convert text to speech", "speak this text",
        "synthesize speech from text", "text to audio"
    ],
    "get_survey_results": [
        "get results", "survey analytics", "show MOS", "get survey responses",
        "show survey dashboard", "view MOS scores", "get survey statistics",
        "survey dashboard", "fetch analytics"
    ],
    "check_health": [
        "health check", "system status", "check backend", "is redis connected",
        "is system healthy", "check service health", "backend status", "health check status"
    ],
    "nlp_analyze": [
        "analyze text", "extract entities", "find POS tags", "linguistic analysis",
        "nlu parse", "nlp analyze", "parse this sentence", "entity recognition"
    ],
    "clear_data": [
        "clear data", "reset survey", "delete responses", "wipe cache",
        "clear survey responses", "reset database", "delete database records",
        "reset survey data", "clear cache records"
    ],
    "get_weather": [
        "weather", "temperature", "forecast", "is it raining", "what is the weather",
        "weather today", "will it rain today", "current weather"
    ]
}

# Lexicon for Sentiment analysis
POSITIVE_LEMMAS = {
    "good", "great", "excellent", "happy", "wonderful", "success", "successful",
    "healthy", "love", "like", "awesome", "perfect", "fantastic", "fine", "nice",
    "glad", "pleased", "satisfying", "satisfied", "beautiful", "amazing", "cool",
    "superb", "outstanding", "enjoy"
}

NEGATIVE_LEMMAS = {
    "bad", "terrible", "poor", "unhappy", "fail", "failed", "failure", "unhealthy",
    "hate", "dislike", "awful", "error", "broken", "wrong", "difficult", "slow",
    "leak", "leaking", "defect", "defective", "sad", "horrible", "ugly", "useless"
}

NEGATION_WORDS = {"not", "no", "never", "n't", "neither", "nor", "none"}

# Pre-tokenize reference items to build vocabulary and target vector representations
reference_lemmas = {}  # maps intent -> list of list of lemmas
vocab = set()

for intent, phrases in INTENTS.items():
    reference_lemmas[intent] = []
    for phrase in phrases:
        # Pre-process referencing documents using spaCy
        doc = nlp(phrase.lower())
        lemmas = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.text.strip()]
        if lemmas:
            reference_lemmas[intent].append(lemmas)
            vocab.update(lemmas)

def get_tf_vector(lemmas, vocabulary):
    vector = {}
    for l in lemmas:
        if l in vocabulary:
            vector[l] = vector.get(l, 0) + 1
    return vector

def dot_product(v1, v2):
    dot = 0.0
    for k, val in v1.items():
        if k in v2:
            dot += val * v2[k]
    return dot

def magnitude(v):
    return math.sqrt(sum(val * val for val in v.values()))

def cosine_similarity(v1, v2):
    mag1 = magnitude(v1)
    mag2 = magnitude(v2)
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot_product(v1, v2) / (mag1 * mag2)

def clean_string(s: str) -> str:
    # Helper to strip spaces, ignore case and normalize spaces
    return " ".join(s.lower().split()).strip()

INTENT_RULES = {
    "greet": {"hello", "hi", "hey", "greetings", "howdy", "morning", "afternoon", "evening"},
    "goodbye": {"goodbye", "bye", "exit", "quit", "terminate", "farewell"},
    "help": {"help", "info", "instructions", "instruction", "assist", "assistance"},
    "transcribe_audio": {"transcribe", "transcription"},
    "synthesize_speech": {"synthesize", "synthesis", "tts"},
    "get_survey_results": {"results", "analytics", "mos", "responses", "dashboard", "statistics"},
    "check_health": {"health", "healthy", "status"},
    "nlp_analyze": {"analyze", "pos", "tag", "tags", "entities", "entity", "linguistic", "parse"},
    "clear_data": {"clear", "reset", "delete", "wipe"},
    "get_weather": {"weather", "temperature", "forecast", "rain", "raining", "snow", "sunny"}
}

def classify_intent(text: str) -> tuple[str, float]:
    """
    Classifies the text into one of the 10 intent classes using rules and similarity.
    Returns:
        (intent_name, confidence)
    """
    cleaned_query = clean_string(text)
    
    # 1. Exact/Rule-based Match
    # If the user input matches any of our reference phrases exactly, return 1.0 confidence
    for intent, phrases in INTENTS.items():
        for phrase in phrases:
            if clean_string(phrase) == cleaned_query:
                return intent, 1.0
                
    # Parse query using spaCy
    doc = nlp(text.lower())
    query_tokens = [token.text.lower() for token in doc if not token.is_punct and token.text.strip()]
    query_lemmas = [token.lemma_.lower() for token in doc if not token.is_punct and token.text.strip()]
    
    # 2. Rule-based keyword matching
    intent_counts = {}
    for intent, keywords in INTENT_RULES.items():
        count = 0
        for token_text, token_lemma in zip(query_tokens, query_lemmas):
            if token_text in keywords or token_lemma in keywords:
                count += 1
        if count > 0:
            intent_counts[intent] = count
            
    if intent_counts:
        # Find the intent with the highest count
        best_rule_intent = max(intent_counts, key=intent_counts.get)
        return best_rule_intent, 1.0

    # 3. Similarity-based Fallback Match
    query_lemmas_filtered = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and token.text.strip()]
    
    if not query_lemmas_filtered:
        return "unknown", 0.0
        
    query_vector = get_tf_vector(query_lemmas_filtered, vocab)
    
    best_intent = "unknown"
    best_score = 0.0
    
    # Compare query vector against all reference lemma vectors
    for intent, phrase_lemmas_list in reference_lemmas.items():
        for ref_lemmas in phrase_lemmas_list:
            ref_vector = get_tf_vector(ref_lemmas, vocab)
            score = cosine_similarity(query_vector, ref_vector)
            if score > best_score:
                best_score = score
                best_intent = intent
                
    # Threshold check: must meet 85% confidence threshold (0.85)
    if best_score >= 0.85:
        return best_intent, round(best_score, 4)
    else:
        return "unknown", 0.0

def extract_entities(doc) -> list[dict]:
    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        }
        for ent in doc.ents
    ]

def extract_pos_tags(doc) -> list[dict]:
    return [
        {
            "text": token.text,
            "pos": token.pos_,
            "tag": token.tag_,
            "dep": token.dep_
        }
        for token in doc
    ]

def extract_sentiment(doc) -> dict:
    score = 0.0
    matches = 0
    tokens = list(doc)
    
    for i, token in enumerate(tokens):
        lemma = token.lemma_.lower()
        
        # Check lookback for negation words (up to 2 tokens back)
        negated = False
        for lookback in range(max(0, i - 2), i):
            if tokens[lookback].text.lower() in NEGATION_WORDS:
                negated = True
                break
                
        if lemma in POSITIVE_LEMMAS:
            score += -1.0 if negated else 1.0
            matches += 1
        elif lemma in NEGATIVE_LEMMAS:
            score += 1.0 if negated else -1.0
            matches += 1
            
    final_score = score / matches if matches > 0 else 0.0
    
    if final_score > 0.1:
        label = "positive"
    elif final_score < -0.1:
        label = "negative"
    else:
        label = "neutral"
        
    return {
        "score": round(final_score, 2),
        "label": label
    }

def analyze_text(text: str) -> dict:
    """
    Parses the text through our wrapped spaCy NLU pipeline.
    Returns structured dict containing:
        - intent
        - confidence
        - entities
        - pos_tags
        - sentiment
    """
    doc = nlp(text)
    intent, confidence = classify_intent(text)
    entities = extract_entities(doc)
    pos_tags = extract_pos_tags(doc)
    sentiment = extract_sentiment(doc)
    
    return {
        "text": text,
        "intent": intent,
        "confidence": confidence,
        "entities": entities,
        "pos_tags": pos_tags,
        "sentiment": sentiment
    }
