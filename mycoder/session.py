"""Session persistence — save and restore conversation state."""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SESSION_DIR = Path.home() / ".mycoder" / "sessions"


class Session:
    def __init__(self, session_id=None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.model = None
        self.messages: list[dict] = []
        self.metadata: dict = {}
        self.dir = SESSION_DIR
        self.dir.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self.dir / f"{self.session_id}.json"

    def save(self):
        data = {
            "session_id": self.session_id,
            "model": self.model,
            "messages": self.messages,
            "metadata": self.metadata,
            "saved_at": datetime.now().isoformat(),
        }
        tmp = self.path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2, default=str)
            tmp.replace(self.path)
            logger.debug("Session saved: %s (%d messages)", self.session_id, len(self.messages))
        except Exception as e:
            logger.error("Failed to save session: %s", e)
            if tmp.exists():
                tmp.unlink()

    def load(self, session_id: str | None = None) -> bool:
        path = self.dir / f"{session_id}.json" if session_id else self.path
        if not path.exists():
            return False

        try:
            with open(path) as f:
                data = json.load(f)
            self.session_id = data.get("session_id", self.session_id)
            self.model = data.get("model")
            self.messages = data.get("messages", [])
            self.metadata = data.get("metadata", {})
            logger.info("Session loaded: %s (%d messages)", self.session_id, len(self.messages))
            return True
        except Exception as e:
            logger.error("Failed to load session %s: %s", path.stem, e)
            return False

    @classmethod
    def latest(cls) -> "Session | None":
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            SESSION_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return None
        session = cls()
        if session.load(files[0].stem):
            return session
        return None

    @classmethod
    def list_sessions(cls, limit: int = 10) -> list[dict]:
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(
            SESSION_DIR.glob("*.json"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        results = []
        for f in files[:limit]:
            try:
                with open(f) as fh:
                    data = json.load(fh)
                user_msgs = [m for m in data.get("messages", []) if m.get("role") == "user"]
                results.append({
                    "id": f.stem,
                    "model": data.get("model", "?"),
                    "messages": len(user_msgs),
                    "saved_at": data.get("saved_at", "?"),
                })
            except Exception:
                pass
        return results
