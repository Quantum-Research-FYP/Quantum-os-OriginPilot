"""
PilotProbe Schema Registry
Loads per-paradigm JSON schemas and provides lookup.
"""
import json
import os
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("pilotprobe.schema_registry")

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "schemas")


class SchemaRegistry:
    """Load and serve JSON schemas per (system_type, msg_type)."""

    def __init__(self):
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._requires_auth: Dict[str, bool] = {}
        self._load_all()

    def _load_all(self):
        """Load all schema files from the schemas directory."""
        for fname in os.listdir(SCHEMA_DIR):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(SCHEMA_DIR, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                system = data.get("system", fname.replace(".json", ""))
                self._schemas[system] = data.get("messages", {})
                self._requires_auth[system] = data.get("requires_auth", False)
                logger.info(f"Loaded {len(self._schemas[system])} schemas for {system}")
            except Exception as e:
                logger.error(f"Failed to load schema {fname}: {e}")

    def get_schema(self, system_type: str, msg_type: str) -> Optional[Dict]:
        """Get JSON schema for a specific (system, message_type) pair."""
        system_schemas = self._schemas.get(system_type, {})
        return system_schemas.get(msg_type)

    def requires_auth(self, system_type: str) -> bool:
        """Check if a system requires authentication before tasks."""
        return self._requires_auth.get(system_type, False)

    def get_known_msg_types(self, system_type: str) -> list:
        """Get list of known message types for a system."""
        return list(self._schemas.get(system_type, {}).keys())
