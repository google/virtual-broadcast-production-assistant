import config
from src.firestore_repo import FirestoreRepo
from src.embeddings import generate_embeddings_for_query
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

firestoreDB = FirestoreRepo(config.DB_COLLECTION_NAME)

def vector_search(query: str, k: int) -> dict[str, str]:
    """
    Firestore vector search implementation
    """
    # Compute query embedding
    qv = generate_embeddings_for_query(query)
    # Perform vector search in Firestore
    results = firestoreDB.vector_search(
        query_vector=qv,
        field='embeddings',
        distance=DistanceMeasure.COSINE,
        limit=k,
    )

    return {
        "results": results,
        "status": "success (Firestore)"
    }
