import os
import time
import cohere
from pinecone import Pinecone   

from config.config import (
    get_cohere_api_key,
    get_pinecone_api_key,
    PINECONE_INDEX_NAME
)


def get_clients():
    """Initializes and returns Cohere and Pinecone clients."""
    try:
        cohere_api_key = get_cohere_api_key()
        if not cohere_api_key:
            raise RuntimeError("Cohere API key not found. Set COHERE_API_KEY in env or config.")

        cohere_client = cohere.Client(api_key=cohere_api_key, timeout=60)

        pinecone_api_key = get_pinecone_api_key()
        if not pinecone_api_key:
            raise RuntimeError("Pinecone API key not found. Set PINECONE_API_KEY in env or config.")

        # instantiate Pinecone
        pinecone_client = Pinecone(api_key=pinecone_api_key)

        return cohere_client, pinecone_client

    except Exception as e:
        raise RuntimeError(f"Failed to initialize API clients: {e}")


def setup_vector_store(chunks, cohere_client, pinecone_client):
    """Sets up Pinecone index and uploads embeddings if empty."""
    try:
        # Create index if missing
        if PINECONE_INDEX_NAME not in pinecone_client.list_indexes().names():
            print(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
            pinecone_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1024,  # Cohere embed-english-v3.0 output size
                metric="cosine"
            )

        # Correct way to connect to index
        index = pinecone_client.Index(PINECONE_INDEX_NAME)

    except Exception as e:
        raise RuntimeError(f"Failed to get or create Pinecone index: {e}")

    # Check if index is empty
    stats = index.describe_index_stats()
    if stats.get("total_vector_count", 0) == 0:
        print("Index empty → embedding and uploading documents...")

        batch_size = 96  # Cohere API batch limit
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            try:
                response = cohere_client.embed(
                    texts=batch_chunks,
                    model="embed-english-v3.0",
                    input_type="search_document"
                )
                embeddings = response.embeddings

                vectors_to_upsert = [
                    {
                        "id": str(i + j),
                        "values": embedding,
                        "metadata": {"text": chunk}
                    }
                    for j, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings))
                ]

                index.upsert(vectors=vectors_to_upsert)
                time.sleep(1)  # avoid hitting rate limits

            except Exception as e:
                raise RuntimeError(f"Error during embedding: {e}")

    return index


def retrieve_context(query, cohere_client, index, n_results=5):
    """Retrieve most relevant chunks for a query."""
    try:
        response = cohere_client.embed(
            texts=[query],
            model="embed-english-v3.0",
            input_type="search_query"
        )
        query_embedding = response.embeddings[0]

        results = index.query(
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True
        )

        similarity_threshold = 0.5
        filtered_matches = [
            match for match in results.get("matches", [])
            if match.get("score", 0) > similarity_threshold
        ]

        if not filtered_matches:
            return []

        return [match["metadata"]["text"] for match in filtered_matches]

    except Exception as e:
        raise RuntimeError(f"Failed to retrieve context: {e}")
