"""Task run state machine — manages created -> running -> paused/stopped/completed.

From the execution plan §12C and tech plan §10:
- Only 'completed' allows formal Excel export.
- Pause stops at a safe checkpoint (between items), not mid-item.
- Stop marks the run as 'stopped'; no formal export is allowed.
"""

from dataclasses import dataclass, field
from enum import Enum
from threading import Event
from typing import Callable


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.CREATED: {RunStatus.RUNNING},
    RunStatus.RUNNING: {RunStatus.PAUSING, RunStatus.STOPPING, RunStatus.COMPLETED, RunStatus.FAILED},
    RunStatus.PAUSING: {RunStatus.PAUSED, RunStatus.FAILED},
    RunStatus.PAUSED: {RunStatus.RUNNING, RunStatus.STOPPING},
    RunStatus.STOPPING: {RunStatus.STOPPED, RunStatus.FAILED},
    RunStatus.STOPPED: set(),
    RunStatus.COMPLETED: set(),
    RunStatus.FAILED: set(),
}

EXPORTABLE_STATUSES = {RunStatus.COMPLETED}
TERMINAL_STATUSES = {RunStatus.COMPLETED, RunStatus.STOPPED, RunStatus.FAILED}
ACTIVE_STATUSES = {RunStatus.RUNNING, RunStatus.PAUSING, RunStatus.STOPPING}


@dataclass
class RunStateMachine:
    """Manages the lifecycle of a single task run."""

    status: RunStatus = RunStatus.CREATED
    _resume_event: Event = field(default_factory=Event)
    _stop_event: Event = field(default_factory=Event)
    on_status_change: Callable[[RunStatus, RunStatus], None] | None = None

    def start(self) -> None:
        self._resume_event.set()
        self._transition_to(RunStatus.RUNNING)

    def request_pause(self) -> None:
        """Request a pause. The engine will stop at the next safe checkpoint."""
        if self.status == RunStatus.RUNNING:
            self._resume_event.clear()
            self._transition_to(RunStatus.PAUSING)

    def confirm_paused(self) -> None:
        """Called by the engine when it has reached a safe checkpoint."""
        if self.status == RunStatus.PAUSING:
            self._transition_to(RunStatus.PAUSED)

    def resume(self) -> None:
        if self.status == RunStatus.PAUSED:
            self._transition_to(RunStatus.RUNNING)
            self._resume_event.set()

    def request_stop(self) -> None:
        if self.status in (RunStatus.RUNNING, RunStatus.PAUSED, RunStatus.PAUSING):
            self._transition_to(RunStatus.STOPPING)
            self._stop_event.set()
            self._resume_event.set()

    def confirm_stopped(self) -> None:
        if self.status == RunStatus.STOPPING:
            self._transition_to(RunStatus.STOPPED)

    def mark_completed(self) -> None:
        if self.status == RunStatus.RUNNING:
            self._transition_to(RunStatus.COMPLETED)

    def mark_failed(self) -> None:
        if self.status in ACTIVE_STATUSES:
            self._transition_to(RunStatus.FAILED)

    @property
    def should_pause(self) -> bool:
        return self.status == RunStatus.PAUSING

    @property
    def should_stop(self) -> bool:
        return self.status == RunStatus.STOPPING

    @property
    def can_export(self) -> bool:
        return self.status in EXPORTABLE_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def wait_if_paused(self, timeout: float = 0.5) -> None:
        """Block until resumed, with a short timeout to allow status checks."""
        while self.status == RunStatus.PAUSED:
            self._resume_event.wait(timeout)
            if self.status != RunStatus.PAUSED:
                break

    def _transition_to(self, target: RunStatus) -> None:
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            return
        old = self.status
        self.status = target
        if self.on_status_change:
            self.on_status_change(old, target)
