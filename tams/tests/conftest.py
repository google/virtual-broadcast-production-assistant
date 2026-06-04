import sys
import os
import uuid
import datetime
import pytest
from unittest.mock import MagicMock

# ----------------- MODULE MOCKING -----------------
# We must mock google.cloud.firestore, google.cloud.storage, and google.auth
# before app.main is imported.

class MockDocumentSnapshot:
    def __init__(self, doc_id, data, exists, reference):
        self.id = doc_id
        self._data = data
        self.exists = exists
        self.reference = reference

    def to_dict(self):
        return self._data

class MockDocumentReference:
    def __init__(self, collection_name, doc_id, db_state):
        self.collection_name = collection_name
        self.id = doc_id
        self.db_state = db_state

    def get(self):
        col = self.db_state.setdefault(self.collection_name, {})
        if self.id in col:
            # Return a copy to avoid mutation side effects
            return MockDocumentSnapshot(self.id, dict(col[self.id]), True, self)
        return MockDocumentSnapshot(self.id, None, False, self)

    def set(self, data, merge=False):
        col = self.db_state.setdefault(self.collection_name, {})
        if merge and self.id in col:
            col[self.id].update(data)
        else:
            col[self.id] = dict(data)

    def update(self, data):
        col = self.db_state.setdefault(self.collection_name, {})
        if self.id not in col:
            col[self.id] = {}
        doc_data = col[self.id]
        
        # Support dot notation updates, e.g. "tags.name"
        for path, val in data.items():
            keys = path.split('.')
            current = doc_data
            for key in keys[:-1]:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
            
            last_key = keys[-1]
            if val is DELETE_FIELD:
                if last_key in current:
                    del current[last_key]
            else:
                current[last_key] = val

    def delete(self):
        col = self.db_state.setdefault(self.collection_name, {})
        if self.id in col:
            del col[self.id]

class MockQuery:
    def __init__(self, collection_name, db_state, filters=None, limit_val=None):
        self.collection_name = collection_name
        self.db_state = db_state
        self.filters = filters or []
        self.limit_val = limit_val

    def where(self, field, operator, value):
        new_filters = list(self.filters)
        new_filters.append((field, operator, value))
        return MockQuery(self.collection_name, self.db_state, new_filters, self.limit_val)

    def limit(self, limit):
        return MockQuery(self.collection_name, self.db_state, self.filters, limit)

    def get(self):
        col = self.db_state.setdefault(self.collection_name, {})
        results = []
        for doc_id, data in col.items():
            match = True
            for field, op, value in self.filters:
                val = data.get(field)
                if op == "==":
                    if val != value:
                        match = False
                        break
                elif op == "<=":
                    if val is None or val > value:
                        match = False
                        break
                elif op == ">=":
                    if val is None or val < value:
                        match = False
                        break
                elif op == "<":
                    if val is None or val >= value:
                        match = False
                        break
                elif op == ">":
                    if val is None or val <= value:
                        match = False
                        break
            if match:
                ref = MockDocumentReference(self.collection_name, doc_id, self.db_state)
                results.append(MockDocumentSnapshot(doc_id, dict(data), True, ref))
        if self.limit_val is not None:
            results = results[:self.limit_val]
        return results

    def stream(self):
        return self.get()

class MockCollectionReference:
    def __init__(self, name, db_state):
        self.name = name
        self.db_state = db_state

    def document(self, doc_id=None):
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        return MockDocumentReference(self.name, doc_id, self.db_state)

    def add(self, data):
        doc_id = str(uuid.uuid4())
        self.document(doc_id).set(data)
        # Returns a tuple of (unused, document_reference) in Firestore API
        return None, self.document(doc_id)

    def limit(self, limit):
        return MockQuery(self.name, self.db_state, limit_val=limit)

    def where(self, field, operator, value):
        return MockQuery(self.name, self.db_state).where(field, operator, value)

    def get(self):
        return MockQuery(self.name, self.db_state).get()

    def stream(self):
        return self.get()

class MockFirestoreClient:
    def __init__(self, database="(default)", *args, **kwargs):
        self.database = database
        self.db_state = {}

    def collection(self, name):
        return MockCollectionReference(name, self.db_state)

DELETE_FIELD = object()

class MockFirestoreModule:
    Client = MockFirestoreClient
    DELETE_FIELD = DELETE_FIELD

# Inject into sys.modules and google package namespaces
import google
if not hasattr(google, 'cloud'):
    class CloudModule:
        pass
    google.cloud = CloudModule()

google.cloud.firestore = MockFirestoreModule
sys.modules['google.cloud.firestore'] = MockFirestoreModule

# Mock Google Cloud Storage Client
class MockBlob:
    def __init__(self, name, bucket):
        self.name = name
        self.bucket = bucket

    def generate_signed_url(self, **kwargs):
        method = kwargs.get("method", "GET")
        return f"https://mock-storage.googleapis.com/{self.bucket.name}/{self.name}?method={method}&mock_signed=true"

class MockBucket:
    def __init__(self, name, client):
        self.name = name
        self.client = client

    def blob(self, name):
        return MockBlob(name, self)

class MockStorageClient:
    def bucket(self, name):
        return MockBucket(name, self)

class MockStorageModule:
    Client = MockStorageClient

google.cloud.storage = MockStorageModule
sys.modules['google.cloud.storage'] = MockStorageModule

# Mock google.auth and dependencies
class MockCredentials:
    token = "mock-access-token"
    def refresh(self, request):
        pass

class MockAuthModule:
    @staticmethod
    def default():
        return MockCredentials(), "mock-project-id"

class MockAuthRequests:
    class Request:
        pass

class MockAuthTransportRequestsModule:
    Request = MockAuthRequests

sys.modules['google.auth'] = MockAuthModule

class MockAuthTransportModule:
    pass

mock_transport = MockAuthTransportModule()
mock_transport.requests = MockAuthTransportRequestsModule

sys.modules['google.auth.transport'] = mock_transport
sys.modules['google.auth.transport.requests'] = MockAuthTransportRequestsModule

google.auth = MockAuthModule
google.auth.transport = mock_transport



# ----------------- FIXTURES -----------------

@pytest.fixture
def mock_db():
    """Fixture that yields the mock firestore client and clears its state before each test."""
    from app.main import db
    db.db_state.clear()
    return db

@pytest.fixture
def client(mock_db):
    """Fixture that yields the FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
