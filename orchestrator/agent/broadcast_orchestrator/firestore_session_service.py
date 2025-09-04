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
from google.adk.events import Event, LLMResponse, UserMessage
from google.adk.sessions import BaseSessionService, Session


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

        # Return a Session object without events, as they are in a subcollection
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

        # Fetch events from the subcollection
        events = []
        events_ref = doc_ref.collection("events").order_by("timestamp").stream()
        async for event_doc in events_ref:
            event_data = event_doc.to_dict()
            # The event type is not directly available in the model dump,
            # so we have to rely on the structure of the event data to
            # determine the type. This is not ideal, but it is the best
            # we can do without a more robust serialization format.
            if "content" in event_data and "author" in event_data:
                if event_data["author"] == "user":
                    events.append(UserMessage(**event_data))
                elif event_data["author"] == "agent":
                    events.append(LLMResponse(**event_data))
                else:
                    events.append(Event(**event_data))
            else:
                events.append(Event(**event_data))

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
        event_ref = session_ref.collection(
            "events"
        ).document()  # Auto-generate event ID

        event_dict = event.model_dump()
        # Ensure a timestamp exists for ordering
        if "timestamp" not in event_dict:
            event_dict["timestamp"] = datetime.datetime.now(datetime.timezone.utc)

        # Atomically create the new event and update the session's last update time
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
        """
        Deletes a session document and its subcollections.
        """
        await self.delete_session_recursively(session_id)

    async def delete_session_recursively(self, session_id: str, batch_size: int = 500):
        """
        Deletes a document and all of its subcollections recursively.
        This is a helper method and not part of the BaseSessionService interface.
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
