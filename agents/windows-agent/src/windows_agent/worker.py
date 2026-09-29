import logging
import signal
import sys
import time
from contracts.tasks.models import TaskStatus, TaskTargetDevice
from windows_agent.client import task_client
from windows_agent.config import settings
from windows_agent.executor import task_executor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("windows_agent")


class WindowsAgentWorker:
    def __init__(self) -> None:
        self.running = False

    def start(self) -> None:
        self.running = True
        logger.info(f"Windows Agent worker started (device_id='{settings.DEVICE_ID}')")
        logger.info(f"Connected to backend: {settings.TASK_SERVICE_URL}")
        logger.info(f"Allowed roots: {[str(r) for r in settings.get_allowed_roots()]}")

        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)

        while self.running:
            try:
                self.poll_and_execute()
            except Exception as e:
                logger.error(f"Error in worker poll loop: {e}", exc_info=True)

            time.sleep(settings.POLL_INTERVAL_SECONDS)

    def poll_and_execute(self) -> int:
        """Polls for pending tasks matching this device and executes them. Returns count handled."""
        try:
            tasks = task_client.list_tasks(status=TaskStatus.PENDING)
        except Exception as e:
            logger.debug(f"Could not connect to task-service: {e}")
            return 0

        handled = 0
        for task in tasks:
            if not self.running:
                break
            if task.target_device in (TaskTargetDevice.WINDOWS, TaskTargetDevice.ANY):
                logger.info(f"Claiming task {task.id}: {task.title}")
                task_executor.execute(task)
                handled += 1

        return handled

    def stop(self) -> None:
        logger.info("Stopping Windows Agent worker...")
        self.running = False

    def _handle_exit(self, signum, frame) -> None:
        self.stop()
        sys.exit(0)


if __name__ == "__main__":
    worker = WindowsAgentWorker()
    worker.start()
