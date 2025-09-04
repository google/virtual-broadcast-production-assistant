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
"""Unit tests for the FirestoreSessionService."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.events import Event
from google.adk.sessions import Session
from google.genai.types import Content, Part as AdkPart

from broadcast_orchestrator.firestore_session_service import (
    FirestoreSessionService,
)


class TestFirestoreSessionService(unittest.TestCase):
    """Unit tests for the FirestoreSessionService."""

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_create_session(self, mock_async_client):
        """Test that a session is created correctly."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.collection.return_value = mock_collection
            mock_doc_ref = MagicMock()
            mock_collection.document.return_value = mock_doc_ref
            mock_doc_ref.set = AsyncMock()

            service = FirestoreSessionService()

            # Act
            session = await service.create_session("test_app", "test_user")

            # Assert
            self.assertIsInstance(session, Session)
            self.assertEqual(session.app_name, "test_app")
            self.assertEqual(session.user_id, "test_user")
            mock_doc_ref.set.assert_called_once()

        asyncio.run(run_test())

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_get_session(self, mock_async_client):
        """Test that a session is retrieved correctly."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.collection.return_value = mock_collection
            mock_doc_ref = MagicMock()
            mock_collection.document.return_value = mock_doc_ref

            mock_doc = MagicMock()
            mock_doc.exists = True
            mock_doc.to_dict.return_value = {
                "id": "test_session",
                "app_name": "test_app",
                "user_id": "test_user",
                "state": {"key": "value"},
            }
            mock_doc_ref.get = AsyncMock(return_value=mock_doc)

            mock_events_ref = MagicMock()
            mock_doc_ref.collection.return_value = mock_events_ref
            mock_events_ref.order_by.return_value = mock_events_ref

            mock_event_doc = MagicMock()
            mock_event_doc.to_dict.return_value = {
                "type": "user_message",
                "content": {"text": "Hello"},
            }

            async def mock_stream():
                yield mock_event_doc

            mock_events_ref.stream.return_value = mock_stream()

            service = FirestoreSessionService()

            # Act
            session = await service.get_session(
                "test_app", "test_user", "test_session"
            )

            # Assert
            self.assertIsInstance(session, Session)
            self.assertEqual(session.id, "test_session")
            self.assertEqual(len(session.events), 1)
            self.assertEqual(session.events[0].author, "user")
            self.assertEqual(session.events[0].content.parts[0].text, "Hello")

        asyncio.run(run_test())

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_append_event(self, mock_async_client):
        """Test that an event is appended correctly."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_batch = MagicMock()
            mock_batch.commit = AsyncMock()
            mock_db.batch.return_value = mock_batch
            mock_session_ref = MagicMock()
            mock_event_ref = MagicMock()
            mock_collection = mock_db.collection.return_value
            mock_collection.document.return_value = mock_session_ref
            mock_session_ref.collection.return_value.document.return_value = (
                mock_event_ref
            )

            service = FirestoreSessionService()

            # Create a mock session object to pass to the method
            mock_session = Session(
                id="test_session",
                app_name="test_app",
                user_id="test_user",
                state={},
                events=[]
            )

            content = Content(parts=[AdkPart(text="Hi")])
            event = Event(author="user", content=content)

            # Act
            await service.append_event(session=mock_session, event=event)

            # Assert
            mock_collection.document.assert_called_once_with("test_session")
            mock_batch.commit.assert_called_once()
            args, _ = mock_batch.set.call_args
            self.assertEqual(args[0], mock_event_ref)
            self.assertEqual(args[1]["type"], "user_message")
            self.assertEqual(args[1]["content"]["text"], "Hi")

        asyncio.run(run_test())

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_list_sessions(self, mock_async_client):
        """Test that sessions are listed correctly."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.collection.return_value = mock_collection
            mock_query = MagicMock()
            mock_collection.where.return_value = mock_query
            mock_query.where.return_value = mock_query
            mock_query.order_by.return_value = mock_query

            mock_doc = MagicMock()
            mock_doc.id = "test_session_1"

            async def mock_stream():
                yield mock_doc

            mock_query.limit.return_value.stream.return_value = mock_stream()

            service = FirestoreSessionService()

            # Act
            session_ids = await service.list_sessions("test_app", "test_user")

            # Assert
            self.assertEqual(len(session_ids), 1)
            self.assertEqual(session_ids[0], "test_session_1")

        asyncio.run(run_test())

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_delete_session_recursively(self, mock_async_client):
        """Test that a session is deleted recursively."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.collection.return_value = mock_collection
            mock_doc_ref = MagicMock()
            mock_collection.document.return_value = mock_doc_ref
            mock_doc_ref.delete = AsyncMock()

            mock_events_ref = MagicMock()
            mock_doc_ref.collection.return_value = mock_events_ref
            mock_limit_query = MagicMock()
            mock_events_ref.limit.return_value = mock_limit_query

            mock_doc = MagicMock()
            mock_limit_query.get = AsyncMock(side_effect=[[mock_doc], []])

            mock_batch = MagicMock()
            mock_batch.commit = AsyncMock()
            mock_db.batch.return_value = mock_batch

            service = FirestoreSessionService()

            # Act
            await service.delete_session_recursively("test_session")

            # Assert
            mock_doc_ref.delete.assert_called_once()
            self.assertEqual(mock_batch.delete.call_count, 1)
            self.assertEqual(mock_batch.commit.call_count, 1)

        asyncio.run(run_test())

    @patch(
        "broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    @patch(
        "broadcast_orchestrator.firestore_session_service.FirestoreSessionService.delete_session_recursively"
    )
    def test_delete_session(self, mock_delete_recursively, mock_async_client):
        """Test that delete_session calls delete_session_recursively."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            service = FirestoreSessionService()

            # Act
            await service.delete_session("test_app", "test_user", "test_session")

            # Assert
            mock_delete_recursively.assert_called_once_with("test_session")

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
