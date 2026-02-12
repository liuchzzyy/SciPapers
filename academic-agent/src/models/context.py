from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path


@dataclass
class ConversationContext:
    """Maintains conversation state across interactions"""

    user_profile: Dict[str, Any] = field(default_factory=dict)
    active_items: Dict[str, Dict] = field(default_factory=dict)
    workflow_history: List[Dict] = field(default_factory=list)
    last_update: datetime = field(default_factory=datetime.now)

    def remember(self, key: str, value: Any) -> None:
        """Store information for later use"""
        self.user_profile[key] = value
        self.last_update = datetime.now()

    def recall(self, key: str, default: Any = None) -> Any:
        """Retrieve previously stored information"""
        return self.user_profile.get(key, default)

    def add_active_item(self, item_key: str, metadata: Dict) -> None:
        """Add currently discussed paper"""
        self.active_items[item_key] = {
            "metadata": metadata,
            "added_at": datetime.now().isoformat(),
        }
        self.last_update = datetime.now()

    def get_active_item(self, item_key: Optional[str] = None) -> Optional[Dict]:
        """Get current or most recent active item"""
        if item_key:
            return self.active_items.get(item_key)
        if self.active_items:
            return max(self.active_items.items(), key=lambda x: x[1]["added_at"])[1]
        return None

    def add_workflow(self, workflow_data: Dict) -> None:
        """Record workflow to history"""
        self.workflow_history.append(
            {"workflow": workflow_data, "timestamp": datetime.now().isoformat()}
        )
        self.last_update = datetime.now()

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "user_profile": self.user_profile,
            "active_items": {
                k: {"metadata": v["metadata"], "added_at": v["added_at"]}
                for k, v in self.active_items.items()
            },
            "workflow_history": [
                {
                    "intent": w["workflow"].get("intent"),
                    "description": w["workflow"].get("description"),
                    "timestamp": w["timestamp"],
                }
                for w in self.workflow_history[-10:]
            ],
            "last_update": self.last_update.isoformat(),
        }

    def save(self, path: str) -> None:
        """Save context to file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "ConversationContext":
        """Load context from file"""
        if not Path(path).exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ctx = cls()
        ctx.user_profile = data.get("user_profile", {})
        ctx.active_items = {
            k: {"metadata": v["metadata"], "added_at": v["added_at"]}
            for k, v in data.get("active_items", {}).items()
        }
        ctx.workflow_history = data.get("workflow_history", [])
        last_update = data.get("last_update")
        if last_update:
            ctx.last_update = datetime.fromisoformat(last_update)
        return ctx
