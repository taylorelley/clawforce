"""Persistence layer: agents, users, plans (SQLite)."""

from specops.core.database import Database, get_database
from specops.core.storage import StorageBackend, get_storage_backend
from specops.core.store.agents import AgentStore
from specops.core.store.base import BaseRepository
from specops.core.store.plans import PlanStore
from specops.core.store.shares import ShareStore
from specops.core.store.users import UserStore


class Store:
    """Facade composing AgentStore, UserStore, PlanStore, and ShareStore.

    Uses a single SQLite Database and optional StorageBackend (for agent workspace).
    """

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self._storage = storage or get_storage_backend()
        db = get_database()
        self.agents = AgentStore(db, self._storage)
        self.users = UserStore(db)
        self.plans = PlanStore(db)
        self.shares = ShareStore(db)


__all__ = [
    "AgentStore",
    "BaseRepository",
    "Database",
    "PlanStore",
    "ShareStore",
    "Store",
    "UserStore",
    "get_database",
]
