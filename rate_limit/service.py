import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

BAN_FILE = Path("logs/bans.json")


class RateLimiter:
    def __init__(self, limit=5, window_seconds=60, cooldown_seconds=120, strike_limit=3, mode="inference"):
        self.mode = mode
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.strike_limit = strike_limit

        self.requests = defaultdict(deque)
        self.strikes = defaultdict(int)
        self.banned_until = self._load_bans()

        self.global_window = deque()

        # for traffic analysis
        self.recent_requests = defaultdict(deque)

    def check(self, user_id, ip_address, mode=None):
        now = datetime.utcnow()
        key = f"{user_id}:{ip_address}"
        active_mode = mode or self.mode

        # COOLDOWN CHECK (unchanged)
        if key in self.banned_until and now < self.banned_until[key]:
            remaining = int((self.banned_until[key] - now).total_seconds())
            return {
                "allowed": False,
                "message": f"Temporary cooldown active. Try again in {remaining} seconds.",
            }

        # TRAINING MODE: relaxed limits, only catch inference-speed abuse
        if active_mode == "training":
            recent = self.recent_requests[key]
            while recent and (now - recent[0]) > timedelta(seconds=10):
                recent.popleft()
            recent.append(now)
            if len(recent) >= 2:
                gap = (recent[-1] - recent[-2]).total_seconds()
                if gap < 0.5:
                    return {
                        "allowed": False,
                        "message": "Requests too fast even for training uploads.",
                    }
            return {"allowed": True, "message": "Training upload allowed."}

        # TRAFFIC ANALYSIS (SHORT WINDOW)
        recent = self.recent_requests[key]

        # Keep only last 10 seconds
        while recent and (now - recent[0]) > timedelta(seconds=10):
            recent.popleft()

        recent.append(now)

        # Burst detection (too many requests in 10 sec)
        if len(recent) > 8:
            return {
                "allowed": False,
                "message": "Burst traffic detected (possible DoS)",
            }

        # Rapid request detection (too fast)
        if len(recent) >= 2:
            time_diff = (recent[-1] - recent[-2]).total_seconds()
            if time_diff < 0.3:
                return {
                    "allowed": False,
                    "message": "Requests too frequent (bot-like behavior)",
                }
            
        # COORDINATED ATTACK DETECTION (inference mode only)
        self.global_window.append((now, ip_address))
        cutoff = now - timedelta(seconds=2)
        while self.global_window and self.global_window[0][0] < cutoff:
            self.global_window.popleft()
        unique_ips = {ip for _, ip in self.global_window}
        if len(unique_ips) >= 5:
            return {
                "allowed": False,
                "message": "Coordinated traffic detected from multiple IPs.",
            }

        # EXISTING LOGIC (UNCHANGED BELOW)

        entries = self.requests[key]
        while entries and now - entries[0] > self.window:
            entries.popleft()

        if len(entries) >= self.limit:
            self.strikes[key] += 1

            if self.strikes[key] >= self.strike_limit:
                self.banned_until[key] = now + self.cooldown
                self._save_bans()
                self.strikes[key] = 0
                return {
                    "allowed": False,
                    "message": "Too many repeated requests. Temporary cooldown applied.",
                }

            return {
                "allowed": False,
                "message": "Rate limit exceeded. Please slow down and try again.",
            }

        entries.append(now)

        return {
            "allowed": True,
            "message": "Request allowed.",
        }

    def _load_bans(self):
        if not BAN_FILE.exists():
            return {}
        try:
            raw = json.loads(BAN_FILE.read_text())
            now = datetime.utcnow()
            return {
                k: datetime.fromisoformat(v)
                for k, v in raw.items()
                if datetime.fromisoformat(v) > now
            }
        except Exception:
            return {}

    def _save_bans(self):
        try:
            BAN_FILE.parent.mkdir(exist_ok=True)
            BAN_FILE.write_text(json.dumps(
                {k: v.isoformat() for k, v in self.banned_until.items()}
            ))
        except Exception:
            pass