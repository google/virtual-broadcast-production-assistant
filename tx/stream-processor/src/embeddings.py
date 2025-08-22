from config import GOOGLE_EMBEDDING_MODEL
from google import genai
from google.genai import types

client = genai.Client()

def generate_embeddings_for_query(content: str) -> list[float]:
    """
    Create an embedding for querying database

    Args:
      content: Text query to make the embedding
    
    Returns:
      List of embeddings for the provided text
    """
    result = client.models.embed_content(
        model=GOOGLE_EMBEDDING_MODEL,
        contents=content,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )
    return result.embeddings[0].values


def generate_embeddings_for_index(entries: list[dict]) -> list[list[float]]:
    """
    Compute embeddings for a list of entries.

    Args:
      entries: list of dicts with keys 'documentId' and 'content'.

    Returns:
      List of list with the 'embeddings'.
    """
    contents = [entry.get('content', '') for entry in entries]
    results = client.models.embed_content(
        model=GOOGLE_EMBEDDING_MODEL,
        contents=contents,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    values = []
    for e in results.embeddings:
        values.append(e.values)
    
    return values
