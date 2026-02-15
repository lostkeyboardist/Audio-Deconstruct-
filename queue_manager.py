"""
Unified master task queue for Audio Utility App.

Processes convert and stem-separation tasks sequentially in a single
worker thread. Thread-safe; designed for later GUI integration.
"""

import threading
import time

from converter_runner import convert_audio
from demucs_runner import separate_stems


class TaskQueue:
    """
    Single-worker task queue. Tasks are processed one at a time in FIFO order.
    All access to self.tasks is protected by a lock.
    """

    def __init__(self):
        self.tasks = []
        self._lock = threading.Lock()
        self._pause_condition = threading.Condition(self._lock)
        self._paused = False
        self._next_id = 0
        self._worker = None
        self._worker_started = False
        # Optional callback(task) invoked after any task status change; set by GUI etc.
        self.on_task_update = None

    def add_task(self, file_path, operation, params):
        """
        Append a new task to the queue.

        Args:
            file_path: Input audio file path (passed as input_path to engine).
            operation: "convert" or "stem".
            params: Dict of kwargs for the engine (e.g. output_dir, output_format
                for convert; output_dir, model, shifts, overlap for stem).

        Returns:
            int: Unique task id.
        """
        with self._lock:
            self._next_id += 1
            task_id = self._next_id
            task = {
                "id": task_id,
                "file_path": file_path,
                "operation": operation,
                "params": params,
                "status": "waiting",
                "result": None,
            }
            self.tasks.append(task)
        return task_id

    def start_processing(self):
        """
        Start the worker thread if not already running.
        Only one worker thread is ever created.
        """
        with self._lock:
            if self._worker_started:
                return
            self._worker_started = True
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def pause(self):
        """Pause the worker; it will block until resume() is called."""
        with self._lock:
            self._paused = True

    def resume(self):
        """Resume the worker if paused."""
        with self._lock:
            self._paused = False
            self._pause_condition.notify_all()

    def _worker_loop(self):
        """
        Runs in background thread. Continuously picks the next "waiting" task,
        runs the appropriate engine, then updates status and result.
        Only one task runs at a time. Blocks while paused.
        """
        while True:
            task = None
            with self._lock:
                while self._paused:
                    self._pause_condition.wait()
                for t in self.tasks:
                    if t["status"] == "waiting":
                        task = t
                        t["status"] = "processing"
                        t["start_time"] = time.time()
                        break

            if task is None:
                time.sleep(0.5)
                continue

            # Notify listener after waiting -> processing (call outside lock to avoid deadlock)
            if self.on_task_update is not None:
                self.on_task_update(task)

            # Run engine outside lock; catch all exceptions so worker thread never crashes
            try:
                if task["operation"] == "convert":
                    result = convert_audio(
                        input_path=task["file_path"],
                        **task["params"],
                    )
                elif task["operation"] == "stem":
                    result = separate_stems(
                        input_path=task["file_path"],
                        **task["params"],
                    )
                else:
                    result = {
                        "status": "failed",
                        "message": f"Unknown operation: {task['operation']}",
                        "output_path": "",
                    }
            except Exception as e:
                result = {
                    "status": "failed",
                    "message": f"Task failed: {type(e).__name__}: {e}",
                    "output_path": "",
                }

            try:
                with self._lock:
                    task["result"] = result
                    task["status"] = (
                        "done" if result.get("status") == "success" else "failed"
                    )
                    task["end_time"] = time.time()

                if self.on_task_update is not None:
                    self.on_task_update(task)
            except Exception:
                pass  # Never crash worker; task already marked in-memory above

            time.sleep(0.1)

    def get_tasks(self):
        """
        Return a copy of the task list for reading (e.g. by GUI).
        Thread-safe.
        """
        with self._lock:
            return list(self.tasks)

    def get_eta(self):
        """
        Estimate seconds remaining for waiting + processing tasks.

        Uses average duration of completed tasks. If none completed yet,
        uses elapsed time of current processing task as provisional average.
        Returns 0.0 when nothing remains or no duration data. Never raises.
        """
        try:
            with self._lock:
                processing_tasks = 0
                waiting_tasks = 0
                completed_durations = []
                processing_elapsed = 0.0

                for t in self.tasks:
                    if t["status"] == "waiting":
                        waiting_tasks += 1
                    elif t["status"] == "processing":
                        processing_tasks += 1
                        if t.get("start_time") is not None:
                            processing_elapsed = time.time() - t["start_time"]
                    elif t.get("start_time") is not None and t.get("end_time") is not None:
                        completed_durations.append(t["end_time"] - t["start_time"])

                remaining_tasks = waiting_tasks + (1 if processing_tasks > 0 else 0)
                if remaining_tasks == 0:
                    return 0.0

                if completed_durations:
                    average_duration = sum(completed_durations) / len(completed_durations)
                elif processing_tasks > 0 and processing_elapsed > 0:
                    average_duration = processing_elapsed
                else:
                    return 0.0

                return average_duration * remaining_tasks
        except Exception:
            return 0.0

    def move_task(self, task_id, direction):
        """
        Move a waiting task up or down in the list. Processing order follows list order.

        Args:
            task_id: Task id to move.
            direction: "up" or "down".

        Returns:
            True if the task was moved, False otherwise (task not found, not waiting, or at boundary).
        """
        with self._lock:
            idx = None
            for i, t in enumerate(self.tasks):
                if t["id"] == task_id:
                    idx = i
                    break
            if idx is None:
                return False
            if self.tasks[idx]["status"] != "waiting":
                return False
            if direction == "up":
                if idx <= 0:
                    return False
                self.tasks[idx], self.tasks[idx - 1] = self.tasks[idx - 1], self.tasks[idx]
                return True
            if direction == "down":
                if idx >= len(self.tasks) - 1:
                    return False
                self.tasks[idx], self.tasks[idx + 1] = self.tasks[idx + 1], self.tasks[idx]
                return True
            return False
