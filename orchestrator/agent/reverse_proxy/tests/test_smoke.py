
import os
import pytest
from unittest.mock import patch

# Set a dummy environment variable before importing the app
# This is necessary because the main.py reads the env var at the global scope.
@pytest.fixture(autouse=True)
def set_env_var():
    with patch.dict(os.environ, {"AGENT_ENGINE_URL": "projects/proj/locations/loc/reasoningEngines/123"}):
        yield

def test_import_app():
    """
    A simple smoke test that tries to import the FastAPI app.
    This will catch any syntax errors or import errors at the global scope,
    which would prevent the container from starting.
    """
    try:
        from main import app
        assert app is not None
    except Exception as e:
        pytest.fail(f"Failed to import FastAPI app: {e}")
