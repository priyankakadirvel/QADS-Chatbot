import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- API Keys ---
def get_cohere_api_key():
    """Returns the Cohere API key from environment variables."""
    return os.getenv("COHERE_API_KEY")

def get_groq_api_key():
    """Returns the Groq API key from environment variables."""
    return os.getenv("GROQ_API_KEY")

def get_pinecone_api_key():
    """Returns the Pinecone API key from environment variables."""
    return os.getenv("PINECONE_API_KEY")

def get_serpapi_api_key():
    """Returns the SerpApi API key from environment variables."""
    return os.getenv("SERPAPI_API_KEY")


# --- App Configuration ---
def get_all_pdf_paths(folder_path):
    """
    Returns a list of full paths for all PDF files in a given folder.
    """
    pdf_paths = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):  # only PDFs
            pdf_paths.append(os.path.join(folder_path, filename))
    return pdf_paths


# Paths & Index Name (resolve relative to q_backend)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # .../q_backend
BOOKS_FOLDER_PATH = os.path.join(BASE_DIR, "books_pdfs")
PINECONE_INDEX_NAME = "qads"

#  Preload all PDFs (optional)
try:
    all_my_books = get_all_pdf_paths(BOOKS_FOLDER_PATH)
    for book_path in all_my_books:
        print(f"Processing file: {book_path}")
    print(f"\nFound {len(all_my_books)} PDF files to process.")
except Exception as e:
    print(f"Warning: Could not list PDFs in {BOOKS_FOLDER_PATH}: {e}")
