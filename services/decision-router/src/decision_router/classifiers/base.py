from abc import ABC, abstractmethod
from contracts.router.models import RouteDecision, RouteRequest


class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, request: RouteRequest) -> RouteDecision:
        """Evaluates user prompt and returns an actionable RouteDecision."""
        pass
