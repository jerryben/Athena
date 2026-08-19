from abc import ABC, abstractmethod


class BaseService(ABC):
    """Base class for all Athena services."""

    @abstractmethod
    def health(self):
        """Return health information."""
        pass