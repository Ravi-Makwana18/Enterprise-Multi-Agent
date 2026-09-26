import threading
import time
import uuid
from collections import defaultdict
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.request_totals: dict[tuple[str, str, str], int] = defaultdict(int)
        self.latency_ms: dict[tuple[str, str], list[float]] = defaultdict(list)
        self.alerts: list[dict[str, Any]] = []

    def record_request(self, method: str, path: str, status_code: int, latency_ms: float) -> None:
        key = (method.upper(), path, str(status_code))
        with self._lock:
            self.request_totals[key] += 1
            self.latency_ms[(method.upper(), path)].append(latency_ms)

        if status_code >= 500 or latency_ms >= 3000:
            self.record_alert(
                kind="latency" if status_code < 500 and latency_ms >= 3000 else "failure",
                severity="warning" if status_code < 500 else "critical",
                message=(
                    f"{method.upper()} {path} exceeded operational threshold: "
                    f"status={status_code}, latency_ms={latency_ms:.2f}"
                ),
            )

    def record_alert(self, kind: str, severity: str, message: str) -> None:
        alert = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "severity": severity,
            "message": message,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with self._lock:
            self.alerts.append(alert)
            if len(self.alerts) > 50:
                self.alerts = self.alerts[-50:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            totals = [
                {
                    "method": method,
                    "path": path,
                    "status": status,
                    "count": count,
                }
                for (method, path, status), count in sorted(self.request_totals.items())
            ]

            latency_summary = []
            for (method, path), values in sorted(self.latency_ms.items()):
                if not values:
                    continue
                latency_summary.append(
                    {
                        "method": method,
                        "path": path,
                        "count": len(values),
                        "avg_ms": round(sum(values) / len(values), 2),
                        "max_ms": round(max(values), 2),
                        "p95_ms": round(sorted(values)[max(0, int(len(values) * 0.95) - 1)], 2),
                    }
                )

            return {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "request_totals": totals,
                "latency_summary": latency_summary,
                "alerts": list(self.alerts),
            }

    def alert_summary(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self.alerts)[-10:]


metrics_registry = MetricsRegistry()


def generate_trace_id(existing: str | None = None) -> str:
    return (existing or uuid.uuid4().hex)[:64]
