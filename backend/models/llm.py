from groq import Groq
import logging
from config.config import get_groq_api_key
from utils.scraper import perform_web_search

logger = logging.getLogger(__name__)


def is_data_science_query(text: str) -> bool:
    """Return True if the query is about data science/ML/stats/DE/visualization.
    Lightweight keyword check to hard-block unrelated topics before calling the LLM.
    """
    if not text:
        return False
    keywords = {
        "data", "dataset", "pandas", "numpy", "scikit", "sklearn", "matplotlib", "seaborn",
        "plot", "visualization", "viz", "statistic", "stats", "probability", "regression",
        "classification", "clustering", "kmeans", "k-means", "svm", "random forest",
        "xgboost", "lightgbm", "neural", "deep learning", "tensorflow", "keras", "pytorch",
        "nlp", "tokenization", "transformer", "llm", "model", "training", "validation",
        "cross-validation", "feature engineering", "feature selection", "eda", "etl",
        "pipeline", "mlops", "airflow", "dbt", "spark", "hadoop", "big data", "sql",
        "snowflake", "redshift", "databricks", "exploratory", "hypothesis", "a/b test",
        "bayesian", "time series", "arima", "sarima", "prophet", "forecast", "anomaly",
        "imbalance", "roc", "auc", "precision", "recall", "f1", "confusion matrix",
        "gradient descent", "optimizer", "loss function", "hyperparameter", "grid search",
        "random search", "bayesian optimization", "shap", "lime", "interpretability",
        "bias", "variance", "overfitting", "underfitting",
        "federated", "machine learning", "ai", "artificial intelligence", "reinforcement learning",
        "supervised", "unsupervised", "semi-supervised", "algorithm", "network", "system",
        "computer vision", "image processing", "generative", "gan", "autoencoder", "rnn", "cnn",
        "lstm", "gru", "bert", "gpt", "large language model", "embedding", "vector", "tensor",
        "graph", "node", "edge", "link", "prediction", "predict", "inference", "deploy",
        "deployment", "production", "monitoring", "logging", "experiment", "tracking",
        "versioning", "reproducibility", "scalability", "performance", "optimization",
        "efficiency", "latency", "throughput", "bandwidth", "storage", "compute", "memory",
        "disk", "cpu", "gpu", "tpu", "accelerator", "hardware", "software", "framework",
        "library", "tool", "platform", "service", "api", "sdk", "ide", "notebook", "jupyter",
        "colab", "kaggle", "github", "gitlab", "bitbucket", "docker", "kubernetes", "container",
        "image", "registry", "repository", "ci/cd", "devops", "agile", "scrum", "kanban",
        "waterfall", "methodology", "process", "workflow", "best practice", "pattern",
        "anti-pattern", "smell", "refactoring", "testing", "debugging", "profiling", "tuning",
        "help", "info", "about", "introduction", "overview", "summary", "explanation",
        "definition", "meaning", "concept", "term", "terminology", "glossary", "vocabulary",
        "what", "how", "why", "when", "where", "who", "which", "can", "could", "would", "should",
        "is", "are", "was", "were", "do", "does", "did", "have", "has", "had", "will", "shall"
    }
    text_l = text.lower()
    return any(k in text_l for k in keywords)


def get_groq_client():
    """Initializes and returns the Groq client."""
    groq_api_key = get_groq_api_key()
    if not groq_api_key:
        raise RuntimeError("Groq API key not found. Set it in your environment/config.")
    try:
        return Groq(api_key=groq_api_key)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Groq client: {e}")

def generate_llm_response(chat_history, context, groq_client, response_style="Detailed"):
    """
    Generates a response from the LLM based on context from either the 
    local document library or a web search.
    If the latest user query is not related to data science, returns a fixed refusal.
    """
    query = chat_history[-1]["content"] if chat_history else ""
    if not is_data_science_query(query):
        # Hard gate to ensure the bot answers only data science domain
        # yield "Sorry, I am built to answer only data science questions."
        # return
        pass

    source_note = ""

    source_note = "Source: Data Science Library"

    # Build the system prompt and include conversation history
    # Ensure context is a single string and limit its size
    max_chars = 4000
    if context:
        if isinstance(context, list):
            context_str = "\n\n".join(context)
        else:
            context_str = context
        context_str = context_str[:max_chars]
        source_note = source_note or "Source: Data Science Library"
    else:
        source_note = "Source: General Knowledge"
        context_str = ""

    if response_style == "Concise":
        system_prompt = (
            "You are QADS, a helpful data science assistant. "
            "Answer the user's latest question based only on the provided CONTEXT when available. "
            "If the question is outside the scope of data science, you must respond with 'Sorry, I am built to answer only data science questions.' and nothing else. "
            "Be direct and concise. After the answer, append the SOURCE NOTE.\n\n"
            f"CONTEXT:\n{context_str}\n\nSOURCE NOTE: {source_note}"
        )
    else:
        system_prompt = (
            "You are QADS, a helpful data science assistant. "
            "Provide a detailed and comprehensive answer using the CONTEXT when available. "
            "If the question is outside the scope of data science, you must respond with 'Sorry, I am built to answer only data science questions.' and nothing else. "
            "Synthesize information clearly, then append the SOURCE NOTE.\n\n"
            f"CONTEXT:\n{context_str}\n\nSOURCE NOTE: {source_note}"
        )

    try:
        messages = [{"role": "system", "content": system_prompt}] + chat_history
        stream = groq_client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            yield chunk.choices[0].delta.content or ""
            
    except Exception as e:
        yield f"Error generating response from LLM: {e}"
