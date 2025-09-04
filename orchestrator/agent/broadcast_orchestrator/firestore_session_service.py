# -*- coding: utf-8 -*-
#
# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""A session service that stores session data in Google Cloud Firestore."""

import datetime
import uuid
from typing import Any, Dict, List, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.async_client import AsyncClient
from google.cloud.firestore_v1.base_query import FieldFilter
from google.adk.events import Event
from google.adk.sessions import BaseSessionService, Session
from google.genai.types import Content, Part as AdkPart


class FirestoreSessionService(BaseSessionService):
    """
    A session service that stores session data in Google Cloud Firestore.
    This implementation uses a subcollection for events.
    """

    def __init__(
        self, project_id: Optional[str] = None, collection_name: str = "sessions"
    ):
        """Initializes the FirestoreSessionService."""
        self.db: AsyncClient = firestore.AsyncClient(project=project_id)
        self.collection = self.db.collection(collection_name)

    def _convert_firestore_doc_to_adk_event(
        self, event_data: dict
    ) -> Optional[Event]:
        """Converts a Firestore event document to an ADK Event object."""
        event_type = event_data.get("type")
        content_data = event_data.get("content")

        if not event_type or not isinstance(content_data, dict):
            return None

        text = content_data.get("text")
        if text is None:
            return None

        author = "unknown"
        if event_type == "user_message":
            author = "user"
        elif event_type == "llm_response":
            author = "agent"

        if author == "unknown":
            return None

        content = Content(parts=[AdkPart(text=text)])
        return Event(author=author, content=content)

    def _convert_adk_event_to_firestore_doc(self, event: Event) -> dict:
        """Converts an ADK Event object to a Firestore document."""
        event_type = "unknown"
        if event.author == "user":
            event_type = "user_message"
        elif event.author == "agent":
            event_type = "llm_response"

        text = ""
        if event.content and event.content.parts:
            text = event.content.parts[0].text

        return {
            "type": event_type,
            "content": {"text": text},
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
        }

    async def create_session(
        self,
        app_name: str,
        user_id: str,
        session_id: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Creates a new session document in Firestore."""
        session_id = session_id or str(uuid.uuid4())
        doc_ref = self.collection.document(session_id)

        session_data = {
            "id": session_id,
            "app_name": app_name,
            "user_id": user_id,
            "state": state or {},
            "last_update_time": datetime.datetime.now(datetime.timezone.utc),
        }

        await doc_ref.set(session_data)

        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=session_data["state"],
            events=[],
        )

    async def get_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> Optional[Session]:
        """Retrieves a session document and its events subcollection from Firestore."""
        doc_ref = self.collection.document(session_id)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        session_data = doc.to_dict()

        events = []
        events_ref = doc_ref.collection("events").order_by("timestamp").stream()
        async for event_doc in events_ref:
            event_data = event_doc.to_dict()
            adk_event = self._convert_firestore_doc_to_adk_event(event_data)
            if adk_event:
                events.append(adk_event)

        return Session(
            id=session_data["id"],
            app_name=session_data["app_name"],
            user_id=session_data["user_id"],
            state=session_data.get("state", {}),
            events=events,
        )

    async def append_event(
        self, app_name: str, user_id: str, session_id: str, event: Event
    ) -> None:
        """Appends an event as a new document in the events subcollection."""
        session_ref = self.collection.document(session_id)
        event_ref = session_ref.collection("events").document()

        event_dict = self._convert_adk_event_to_firestore_doc(event)

        batch = self.db.batch()
        batch.set(event_ref, event_dict)
        batch.update(session_ref, {"last_update_time": event_dict["timestamp"]})
        await batch.commit()

    async def list_sessions(
        self, app_name: str, user_id: str, limit: int = 100
    ) -> List[str]:
        """Lists session IDs from Firestore for a given user and app."""
        query = self.collection.where(filter=FieldFilter("app_name", "==", app_name))
        query = query.where(filter=FieldFilter("user_id", "==", user_id))
        query = query.order_by(
            "last_update_time", direction=firestore.Query.DESCENDING
        )

        docs = query.limit(limit).stream()
        return [doc.id async for doc in docs]

    async def delete_session(
        self, app_name: str, user_id: str, session_id: str
    ) -> None:
        """Deletes a session document and its subcollections."""
        await self.delete_session_recursively(session_id)

    async def delete_session_recursively(self, session_id: str, batch_size: int = 500):
        """
        Deletes a document and all of its subcollections recursively.
        """
        coll_ref = self.collection.document(session_id).collection("events")
        docs = await coll_ref.limit(batch_size).get()
        while docs:
            batch = self.db.batch()
            for doc in docs:
                batch.delete(doc.reference)
            await batch.commit()
            if len(docs) < batch_size:
                break
            docs = await coll_ref.limit(batch_size).get()

        await self.collection.document(session_id).delete()
