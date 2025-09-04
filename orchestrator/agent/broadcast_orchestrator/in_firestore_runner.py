"""
 Copyright 2025 Google LLC

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 """
# InFirestoreRunner - completely experimental
from typing import Optional
from google.adk.runners import Runner
from google.adk.plugins import BasePlugin
from google.adk.agents import BaseAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService
from .firestore_session_service import FirestoreSessionService


class InFirestoreRunner(Runner):
    """A runner that uses Firestore for Session Management"""

    def __init__(
        self,
        agent: BaseAgent,
        *,
        app_name: str = 'InMemoryRunner',
        plugins: Optional[list[BasePlugin]] = None,
    ):
        """Initializes the InMemoryRunner.

        Args:
            agent: The root agent to run.
            app_name: The application name of the runner. Defaults to
            'InMemoryRunner'.
        """
        self._in_firestore_session_service = FirestoreSessionService()
        super().__init__(
            app_name=app_name,
            agent=agent,
            artifact_service=InMemoryArtifactService(),
            plugins=plugins,
            session_service=self._in_firestore_session_service,
            memory_service=InMemoryMemoryService(),
        )
