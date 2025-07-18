import datetime
import config as config
from logger import logger
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
firebase_admin.initialize_app(cred)

class FirestoreRepo:
    def __init__(self, collection_name: str):
        """Initialize repository with a specific collection."""
        self._client = firestore.client()
        self._collection = self._client.collection(collection_name)

    
    def get_all(self) -> list[dict]:
        """Return all documents in the collection as a list of dicts."""
        docs = []
        for doc in self._collection.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            docs.append(data)
        return docs

    
    def add(self, data: dict) -> str:
        """Add a new document with an auto-generated ID and return that ID."""
        doc_ref, _ = self._collection.add(data)
        return doc_ref.id
    
    
    def search_in_range(self, target_time: datetime.datetime | None = None, delta_seconds: int = 600) -> list[dict]:
        """
        Return documents with an 'embedding' field whose 'timestamp' is within ±delta_seconds of target_time.
        Defaults to the last 10 minutes if target_time is None.
        Returns a list of dicts with keys 'documentId' and 'embedding'.
        """
        # Determine the target_time (default: now UTC)
        if target_time is None:
            target_time = datetime.datetime.now(datetime.timezone.utc)
        start = target_time - datetime.timedelta(seconds=delta_seconds)
        end = target_time + datetime.timedelta(seconds=delta_seconds)

        query = (
            self._collection
                .where(filter=FieldFilter("timestamp", ">=", start))
                .where(filter=FieldFilter("timestamp", "<=", end))
        )
        results = []
        for doc in query.stream():
            data = doc.to_dict()
            vector = data.get('embedding')
            if vector is None:
                continue
            results.append({
                'documentId': doc.id,
                'embedding': vector
            })
        return results


    def batch_add(self, entries: list[dict], embeddings: list[list[float]]) -> None:
        """
        Add multiple documents in a single batch write.
        Each entry in `entries` is a dict to store.
        Returns a list of dicts with keys 'documentId' and 'content'.
        """
        batch = self._client.batch()
        logger.debug(f"Adding {len(entries)} documents to collection")
        for idx, data in enumerate(entries):
            # Create a document with an auto-generated ID
            doc_ref = self._collection.document()
            embedding = next(iter(embeddings[idx:idx+1]), [])
            data["embeddings"] = Vector(embedding)
            batch.set(doc_ref, data)
        # Commit all writes in one request
        batch.commit()


    def update(self, embedding_entries: list[dict]) -> None:
        """
        Update multiple documents in Firestore with their embeddings.
        
        :param embedding_entries: List of dicts, each containing:
            - 'documentId': the Firestore document ID
            - 'embeddings': list of floats representing the embedding vector
        """
        logger.debug(f"Updating {len(embedding_entries)} documents with embeddings")
        for entry in embedding_entries:
            doc_id = entry['documentId']
            emb = entry['embeddings']
            # Update the 'embedding' field of the document
            self._collection.document(doc_id).update({'vector_field':  Vector(emb)})


    def vector_search(
        self,
        query_vector: list[float],
        field: str = 'vector_field',
        distance: DistanceMeasure = DistanceMeasure.COSINE,
        limit: int = 20,
        pre_filters: list[tuple[str, str, any]] = None,
    ) -> list[dict]:
        """
        Make a vectorial search KNN native in Firestore.
        :param query_vector: Embedding query.
        :param field: Vector field name.
        :param distance: Distance (COSINE, EUCLIDEAN, DOT_PRODUCT).
        :param limit: query limit.
        :param pre_filters: pre filters.
        :return: List of documents.
        """
        coll = self._collection
        # Apply previous filters
        if pre_filters:
            for fld, op, val in pre_filters:
                coll = coll.where(fld, op, val)

        vector = Vector(query_vector)
        query = coll.find_nearest(
            vector_field=field,
            query_vector=vector,
            distance_measure=distance,
            limit=limit,
        )

        results = []
        for doc in query.stream():
            data = doc.to_dict()
            results.append({
              # 'documentId': doc_id,
              'timecode': data.get('timecode'),
              'type': data.get('type'),
              'tags': data.get('tags'),
              'content': data.get('content'),
              # 'distance': float(dist)
            })

        return results
