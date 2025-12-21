import os
import logging
import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

def load_and_chunk_pdfs(folder_path):
    """
    Loads all PDF files from a folder using the robust PyMuPDF library,
    extracts their text, and splits it into manageable chunks.
    """
    if not os.path.isdir(folder_path):
        logger.error(f"The path '{folder_path}' is not a valid directory.")
        raise FileNotFoundError(f"Invalid books folder: {folder_path}")

    all_chunks = []
    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

    if not pdf_files:
        logger.warning(f"No PDF files found in '{folder_path}'.")
        raise RuntimeError("No PDF files found to index.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    files_processed = 0
    logger.info("Initializing PDF processing...")

    for i, pdf_file in enumerate(pdf_files):
        file_path = os.path.join(folder_path, pdf_file)
        logger.info(f"Processing {pdf_file} ({i + 1}/{len(pdf_files)})")

        try:
            with fitz.open(file_path) as doc:
                text = ""
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        text += page_text

            if text.strip():
                chunks = text_splitter.split_text(text)
                all_chunks.extend(chunks)
                files_processed += 1

        except Exception as e:
            logger.warning(f"Could not process '{pdf_file}'. Skipping. Error: {e}")
            continue

    logger.info(f"Successfully processed and chunked {files_processed} out of {len(pdf_files)} PDF files.")
    return all_chunks
