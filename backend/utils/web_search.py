from serpapi import GoogleSearch
from config.config import get_serpapi_api_key
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

# Lazy-load Zero-Shot Classifier for non-Streamlit environments
_intent_classifier = None

def load_intent_classifier():
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    return _intent_classifier

# Only allow data science questions
DOMAIN_LABELS = ["data science"]

def is_data_science_query(query: str, threshold: float = 0.75) -> bool:
    """Return True only if 'data science' label score is highest and above threshold."""
    clf = load_intent_classifier()
    result = clf(query, DOMAIN_LABELS)
    labels = result["labels"]
    scores = result["scores"]

    return labels[0] == "data science" and scores[0] >= threshold

def serpapi_web_search(query):
    try:
        # Strict domain intent detection for data science only
        if not is_data_science_query(query):
            return (
                "Sorry, I can answer only Data Science topics. "
                "Please ask something related to Data Science (Machine Learning, Python, Statistics, etc.)."
            )

        serpapi_api_key = get_serpapi_api_key()
        if not serpapi_api_key:
            logger.warning("SerpApi API key not found. Web search will be disabled.")
            return ""

        params = {
            "q": query,
            "api_key": serpapi_api_key,
            "engine": "google",
        }

        search = GoogleSearch(params)
        results = search.get_dict()

        organic_results = results.get("organic_results", [])

        if not organic_results:
            return "No relevant results found for your Data Science query."

        results_str = "\n\n".join(
            f"**Title:** {res.get('title', 'N/A')}\n"
            f"**Link:** {res.get('link', 'N/A')}\n"
            f"**Snippet:** {res.get('snippet', 'N/A')}"
            for res in organic_results[:3]
        )
        return results_str

    except Exception as e:
        logger.error(f"An error occurred during web search: {e}")
        return "An error occurred while processing your request."
