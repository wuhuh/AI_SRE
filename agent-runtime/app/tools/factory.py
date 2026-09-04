from __future__ import annotations

from app.cache import CachedToolRegistry
from app.tools.builtin_tools import (
    DatabaseTool,
    KubernetesTool,
    LogTool,
    PrometheusTool,
    RedisTool,
    TraceTool,
)
from app.tools.registry import ToolRegistry


def create_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(PrometheusTool())
    registry.register(LogTool())
    registry.register(TraceTool())
    registry.register(KubernetesTool())
    registry.register(RedisTool())
    registry.register(DatabaseTool())
    return CachedToolRegistry(registry, ttl_seconds=5)