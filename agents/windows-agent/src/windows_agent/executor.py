import logging
from typing import Any, Dict
from contracts.approvals.models import ApprovalStatus
from contracts.files.models import FileActionType
from contracts.tasks.models import TaskResponse, TaskStatus
from windows_agent.client import TaskServiceClient, task_client
from windows_agent.tools.file_tools import FileTools, file_tools

logger = logging.getLogger("windows_agent.executor")


class TaskExecutor:
    def __init__(
        self,
        client: TaskServiceClient = task_client,
        tools: FileTools = file_tools,
    ) -> None:
        self.client = client
        self.tools = tools

    def execute(self, task: TaskResponse) -> None:
        """Executes a single task dispatched to this Windows worker."""
        logger.info(f"Starting execution of task {task.id}: '{task.title}'")
        self.client.update_task(task.id, status=TaskStatus.RUNNING)

        try:
            payload = task.payload or {}
            action_str = payload.get("action")

            if not action_str:
                raise ValueError("Task payload missing required 'action' field.")

            try:
                action = FileActionType(action_str)
            except ValueError:
                raise ValueError(f"Unsupported action: '{action_str}'")

            if action == FileActionType.LIST_DIRECTORY:
                self._handle_list(task, payload)
            elif action == FileActionType.SEARCH_FILES:
                self._handle_search(task, payload)
            elif action == FileActionType.MOVE_FILE:
                self._handle_move(task, payload)
            elif action == FileActionType.ORGANIZE_FOLDER:
                self._handle_organize(task, payload)
            else:
                raise NotImplementedError(f"Action '{action}' is not implemented.")

        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}", exc_info=True)
            self.client.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e),
            )

    def _handle_list(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        folder = payload.get("directory_path")
        recursive = payload.get("recursive", False)
        items = self.tools.list_directory(folder, recursive=recursive)

        summary = f"Listed {len(items)} items in '{folder}'."
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
        )

    def _handle_search(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        folder = payload.get("directory_path")
        pattern = payload.get("pattern", "*")
        recursive = payload.get("recursive", True)
        matches = self.tools.search_files(folder, pattern=pattern, recursive=recursive)

        summary = f"Found {len(matches)} files matching '{pattern}' in '{folder}'."
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
        )

    def _handle_move(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        src = payload.get("source_path")
        dest = payload.get("destination_path")
        overwrite = payload.get("overwrite", False)
        require_approval = payload.get("require_approval", True)

        if require_approval:
            # Enforce human authorization gate
            approval = self.client.request_approval(
                task_id=task.id,
                action_type="file_move",
                description=f"Move '{src}' to '{dest}'",
                details={"source": src, "destination": dest, "overwrite": overwrite},
            )
            # Wait for human resolution
            resolved = self.client.poll_approval(approval.id, timeout_seconds=300.0)
            if resolved.status != ApprovalStatus.APPROVED:
                reason = resolved.rejection_reason or "Action was not approved by user."
                self.client.update_task(
                    task.id,
                    status=TaskStatus.FAILED,
                    error_message=f"Move operation rejected: {reason}",
                )
                return

        result = self.tools.move_file(src, dest, overwrite=overwrite)
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=result.message,
        )

    def _handle_organize(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        folder = payload.get("directory_path")
        strategy = payload.get("strategy", "by_extension")
        dry_run = payload.get("dry_run", False)

        preview = self.tools.preview_organize(folder, strategy=strategy)
        total_files = preview["total_files"]

        if dry_run or total_files == 0:
            summary = f"Preview: {total_files} files would be organized into {len(preview['categories'])} categories."
            self.client.update_task(
                task.id,
                status=TaskStatus.COMPLETED,
                result_summary=summary,
            )
            return

        # Bulk changes require human approval
        approval = self.client.request_approval(
            task_id=task.id,
            action_type="folder_organize",
            description=f"Organize {total_files} files in '{folder}' into category folders ({list(preview['categories'].keys())})",
            details=preview,
        )

        resolved = self.client.poll_approval(approval.id, timeout_seconds=300.0)
        if resolved.status != ApprovalStatus.APPROVED:
            reason = resolved.rejection_reason or "Folder reorganization rejected by user."
            self.client.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=f"Reorganization rejected: {reason}",
            )
            return

        result = self.tools.execute_organize(folder, strategy=strategy)
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=result.message,
        )


task_executor = TaskExecutor()
