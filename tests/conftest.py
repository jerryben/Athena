import sys
from unittest.mock import MagicMock

# Prevent qdrant_service from connecting during test collection/import
_mock = MagicMock()
_mock.qdrant_service = MagicMock()
sys.modules['backend.services.qdrant_service'] = _mock
