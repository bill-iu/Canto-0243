"""Immutable candidate pools behind opaque workbench snapshot handles."""

from __future__ import annotations

from dataclasses import dataclass
import json
import sys
from threading import RLock
from time import monotonic
from typing import Callable
from uuid import uuid4

from app.schemas.workbench_schema import ReplacementPlanV1, WorkbenchCandidateResponse
from app.services.workbench.replacement_planner import (
    ReplacementSnapshot,
    build_replacement_snapshot,
    page_replacement_snapshot,
)


@dataclass(slots=True)
class _Snapshot:
    identity: str
    value: ReplacementSnapshot
    retained_bytes: int
    last_used: float


@dataclass(frozen=True, slots=True)
class CandidateSnapshotPage:
    snapshot_id: str
    response: WorkbenchCandidateResponse
    restarted: bool = False


def candidate_snapshot_identity(plan: ReplacementPlanV1) -> str:
    """Canonical query identity; draft version and paging are deliberately absent."""
    slots = sorted(
        (slot.model_dump(by_alias=True, exclude_none=True) for slot in plan.slots),
        key=lambda slot: json.dumps(slot, ensure_ascii=False, sort_keys=True),
    )
    return json.dumps(
        {
            "version": plan.version,
            "width": plan.width,
            "mode": plan.mode,
            "slots": slots,
            "semanticIntent": plan.semantic_intent,
            "semanticSeed": plan.semantic_seed,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class CandidateSnapshotStore:
    """Own workbench snapshots for one Desktop process."""

    def __init__(
        self,
        *,
        idle_ttl_seconds: float = 600.0,
        max_bytes: int = 32 * 1024 * 1024,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._snapshots: dict[str, _Snapshot] = {}
        self._idle_ttl_seconds = idle_ttl_seconds
        self._max_bytes = max_bytes
        self._clock = clock
        self._lock = RLock()

    @staticmethod
    def _retained_bytes(snapshot: ReplacementSnapshot) -> int:
        size = sys.getsizeof(snapshot) + sys.getsizeof(snapshot.candidates)
        for item in snapshot.candidates:
            size += sys.getsizeof(item)
        pool = snapshot.pool
        for name in ("syns", "semantic"):
            for item in getattr(pool, name, []) if pool is not None else []:
                size += sys.getsizeof(item)
                if isinstance(item, dict):
                    size += sum(sys.getsizeof(key) + sys.getsizeof(value) for key, value in item.items())
        if snapshot.relaxation is not None:
            size += len(snapshot.relaxation.model_dump_json().encode("utf-8"))
        return size

    def _evict_locked(self, now: float, *, protect: str | None = None) -> None:
        expired = [
            snapshot_id
            for snapshot_id, snapshot in self._snapshots.items()
            if now - snapshot.last_used > self._idle_ttl_seconds
        ]
        for snapshot_id in expired:
            self._snapshots.pop(snapshot_id, None)

        retained = sum(snapshot.retained_bytes for snapshot in self._snapshots.values())
        for snapshot_id, snapshot in sorted(
            self._snapshots.items(),
            key=lambda item: item[1].last_used,
        ):
            if retained <= self._max_bytes:
                break
            if snapshot_id == protect:
                continue
            retained -= snapshot.retained_bytes
            self._snapshots.pop(snapshot_id, None)

    def invalidate_all(self) -> None:
        """Release every handle after lexicon or relation identity changes."""
        with self._lock:
            self._snapshots.clear()

    def stats(self) -> dict[str, int]:
        with self._lock:
            sizes = [snapshot.retained_bytes for snapshot in self._snapshots.values()]
        return {
            "snapshotCount": len(sizes),
            "retainedBytes": sum(sizes),
            "largestSnapshotBytes": max(sizes, default=0),
        }

    def page(
        self,
        plan: ReplacementPlanV1,
        db,
        *,
        snapshot_id: str | None = None,
    ) -> CandidateSnapshotPage:
        identity = candidate_snapshot_identity(plan)
        now = self._clock()
        with self._lock:
            self._evict_locked(now, protect=snapshot_id)
            snapshot = self._snapshots.get(snapshot_id or "")
            if snapshot is not None and snapshot.identity == identity:
                snapshot.last_used = now
        restarted = snapshot_id is not None and (
            snapshot is None or snapshot.identity != identity
        )
        if snapshot is None or snapshot.identity != identity:
            if snapshot_id is not None:
                with self._lock:
                    self._snapshots.pop(snapshot_id, None)
            built = build_replacement_snapshot(plan, db)
            snapshot = _Snapshot(
                identity=identity,
                value=built,
                retained_bytes=self._retained_bytes(built),
                last_used=now,
            )
            snapshot_id = uuid4().hex
            with self._lock:
                self._snapshots[snapshot_id] = snapshot
                self._evict_locked(now, protect=snapshot_id)

        effective_plan = plan.model_copy(update={"offset": 0}) if restarted else plan
        response = page_replacement_snapshot(effective_plan, snapshot.value)
        return CandidateSnapshotPage(
            snapshot_id=snapshot_id,
            response=response,
            restarted=restarted,
        )


candidate_snapshot_store = CandidateSnapshotStore()


__all__ = [
    "CandidateSnapshotPage",
    "CandidateSnapshotStore",
    "candidate_snapshot_store",
    "candidate_snapshot_identity",
]
