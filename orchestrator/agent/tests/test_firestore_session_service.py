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
import datetime
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from google.adk.events import Event, LLMResponse, UserMessage
from google.adk.sessions import Session

from orchestrator.agent.broadcast_orchestrator.firestore_session_service import (
    FirestoreSessionService,
)


class TestFirestoreSessionService(unittest.TestCase):
    """Unit tests for the FirestoreSessionService."""

    @patch(
        "orchestrator.agent.broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
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
        "orchestrator.agent.broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
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
            mock_event_doc.to_dict.return_value = LLMResponse(
                content="Hello"
            ).model_dump()

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

        asyncio.run(run_test())

    @patch(
        "orchestrator.agent.broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
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

            service = FirestoreSessionService()
            event = UserMessage(content="Hi")

            # Act
            await service.append_event("test_app", "test_user", "test_session", event)

            # Assert
            mock_batch.commit.assert_called_once()

        asyncio.run(run_test())

    @patch(
        "orchestrator.agent.broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
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
        "orchestrator.agent.broadcast_orchestrator.firestore_session_service.firestore.AsyncClient"
    )
    def test_delete_session(self, mock_async_client):
        """Test that a session is deleted correctly."""

        async def run_test():
            # Arrange
            mock_db = MagicMock()
            mock_async_client.return_value = mock_db
            mock_collection = MagicMock()
            mock_db.collection.return_value = mock_collection
            mock_doc_ref = MagicMock()
            mock_collection.document.return_value = mock_doc_ref
            mock_doc_ref.delete = AsyncMock()

            service = FirestoreSessionService()

            # Act
            await service.delete_session("test_app", "test_user", "test_session")

            # Assert
            mock_doc_ref.delete.assert_called_once()

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
