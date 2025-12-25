import json
import os
import time
from typing import Dict, List


class TradeLogger:
    def __init__(self, path: str = "data/trades.jsonl", max_hours: int = 24, carry_hours: int = 3):
        self.path = path
        self.max_hours = max_hours
        self.carry_hours = carry_hours
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _read_entries(self) -> List[Dict]:
        entries: List[Dict] = []
        if not os.path.exists(self.path):
            return entries
        with open(self.path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    def _write_entries(self, entries: List[Dict]) -> None:
        with open(self.path, "w", encoding="utf-8") as fh:
            for entry in entries:
                fh.write(json.dumps(entry) + "\n")

    def rollover_if_needed(self) -> None:
        entries = self._read_entries()
        if not entries:
            return
        now = time.time()
        oldest_ts = entries[0].get("ts", now)
        if now - oldest_ts < self.max_hours * 3600:
            return
        cutoff = now - self.carry_hours * 3600
        carried = [e for e in entries if e.get("ts", 0) >= cutoff]
        archive_path = f"{self.path}.archive"
        try:
            with open(archive_path, "a", encoding="utf-8") as fh:
                for entry in entries:
                    fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass
        self._write_entries(carried)

    def log_trade(self, trade: Dict) -> None:
        self.rollover_if_needed()
        entry = {"ts": time.time(), "trade": trade}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def recent_trades(self, hours: int = 24) -> List[Dict]:
        entries = self._read_entries()
        cutoff = time.time() - hours * 3600
        return [e for e in entries if e.get("ts", 0) >= cutoff]
