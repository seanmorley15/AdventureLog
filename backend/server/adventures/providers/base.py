from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class ProviderResult(Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
