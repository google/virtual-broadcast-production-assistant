import datetime
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

_DB = None

def _init_firebase_if_needed():
    """Initialize Firebase Admin + Firestore client lazily.
    - Uses FIRESTORE_PROJECT_ID or GOOGLE_CLOUD_PROJECT for project scoping.
    - Uses GOOGLE_APPLICATION_CREDENTIALS if present (local); otherwise ADC (Cloud Run).
    """
    global _DB
    if _DB is not None:
        return

    project_id = os.getenv("FIRESTORE_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    options = {"projectId": project_id} if project_id else None

    if not firebase_admin._apps:
        if key_path and os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, options=options)
        else:
            # In Cloud Run, use ADC without a key file.
            firebase_admin.initialize_app(options=options)

    _DB = firestore.client()


class FirestoreRepo:
    def __init__(self, collection_name: str):
        """Initialize repository with a specific collection."""
        _init_firebase_if_needed()
        self._client = _DB
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
