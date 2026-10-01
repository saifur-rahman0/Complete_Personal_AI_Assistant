import logging
from typing import Any, Dict
from contracts.approvals.models import ApprovalStatus
from contracts.desktop.models import (
    AllowlistedCommandType,
    DesktopActionType,
)
from contracts.files.models import FileActionType
from contracts.tasks.models import TaskResponse, TaskStatus
from windows_agent.client import TaskServiceClient, task_client
from windows_agent.tools.app_tools import AppTools, app_tools
from windows_agent.tools.file_tools import FileTools, file_tools
from windows_agent.tools.script_tools import ScriptTools, script_tools
from windows_agent.tools.telemetry_tools import TelemetryTools, telemetry_tools

logger = logging.getLogger("windows_agent.executor")


class TaskExecutor:
    def __init__(
        self,
        client: TaskServiceClient = task_client,
        tools: FileTools = file_tools,
        telemetry: TelemetryTools = telemetry_tools,
        apps: AppTools = app_tools,
        scripts: ScriptTools = script_tools,
    ) -> None:
        self.client = client
        self.tools = tools
        self.telemetry = telemetry
        self.apps = apps
        self.scripts = scripts


    def execute(self, task: TaskResponse) -> None:
        """Executes a single task dispatched to this Windows worker."""
        logger.info(f"Starting execution of task {task.id}: '{task.title}'")
        self.client.update_task(task.id, status=TaskStatus.RUNNING)

        try:
            payload = task.payload or {}
            action_str = payload.get("action")

            if not action_str:
                raise ValueError("Task payload missing required 'action' field.")

            # Resolve action to either FileActionType or DesktopActionType
            action = None
            try:
                action = FileActionType(action_str)
            except ValueError:
                try:
                    action = DesktopActionType(action_str)
                except ValueError:
                    raise ValueError(f"Unsupported action: '{action_str}'")

            # Route file actions
            if isinstance(action, FileActionType):
                if action == FileActionType.LIST_DIRECTORY:
                    self._handle_list(task, payload)
                elif action == FileActionType.SEARCH_FILES:
                    self._handle_search(task, payload)
                elif action == FileActionType.READ_FILE:
                    self._handle_read_file(task, payload)
                elif action == FileActionType.OPEN_FILE:
                    self._handle_open_file(task, payload)
                elif action == FileActionType.MOVE_FILE:
                    self._handle_move(task, payload)
                elif action == FileActionType.RENAME_FILE:
                    self._handle_rename(task, payload)
                elif action == FileActionType.DELETE_FILE:
                    self._handle_delete(task, payload)
                elif action == FileActionType.ORGANIZE_FOLDER:
                    self._handle_organize(task, payload)
                else:
                    raise NotImplementedError(f"File action '{action}' is not implemented.")

            # Route desktop actions
            elif isinstance(action, DesktopActionType):
                if action == DesktopActionType.SYSTEM_TELEMETRY:
                    self._handle_system_telemetry(task, payload)
                elif action == DesktopActionType.APP_LAUNCH:
                    self._handle_app_launch(task, payload)
                elif action == DesktopActionType.APP_CLOSE:
                    self._handle_app_close(task, payload)
                elif action == DesktopActionType.LIST_WINDOWS:
                    self._handle_list_windows(task, payload)
                elif action == DesktopActionType.RUN_ALLOWLISTED_COMMAND:
                    self._handle_allowlisted_command(task, payload)
                else:
                    raise NotImplementedError(f"Desktop action '{action}' is not implemented.")

        except Exception as e:
            logger.error(f"Task {task.id} failed: {str(e)}", exc_info=True)
            self.client.update_task(
                task.id,
                status=TaskStatus.FAILED,
                error_message=str(e),
            )

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _handle_list(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        folder = payload.get("directory_path")
        recursive = payload.get("recursive", False)
        items = self.tools.list_directory(folder, recursive=recursive)

        # Sort: directories first, then alphabetical
        items = sorted(items, key=lambda x: (not x.is_directory, x.name.lower()))

        lines = [f"Found {len(items)} item(s) in `{folder}`:\n"]
        for it in items[:60]:
            icon = "📁" if it.is_directory else "📄"
            size_label = "Folder" if it.is_directory else self._format_file_size(it.size_bytes)
            lines.append(f"{icon} [{it.name}]({it.path}) — `{size_label}`")

        if len(items) > 60:
            lines.append(f"\n*... and {len(items) - 60} more items.*")
        elif not items:
            lines.append("*(This folder is empty)*")

        summary = "\n".join(lines)
        result_data = {
            "type": "folder_list",
            "folder": str(folder),
            "count": len(items),
            "files": [
                {
                    "name": it.name,
                    "path": it.path,
                    "is_directory": it.is_directory,
                    "size_bytes": it.size_bytes,
                    "size_formatted": "Folder" if it.is_directory else self._format_file_size(it.size_bytes),
                }
                for it in items
            ],
        }

        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
            result_data=result_data,
        )

    def _handle_search(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        folder = payload.get("directory_path")
        pattern = payload.get("pattern", "*")
        recursive = payload.get("recursive", True)
        matches = self.tools.search_files(folder, pattern=pattern, recursive=recursive)

        matches = sorted(matches, key=lambda x: (not x.is_directory, x.name.lower()))

        folder_label = f"`{folder}`" if folder and str(folder).strip() else "Downloads & Documents"
        lines = [f"Found {len(matches)} file(s) matching `{pattern}` in {folder_label}:\n"]
        for it in matches[:60]:
            icon = "📁" if it.is_directory else "📄"
            size_label = "Folder" if it.is_directory else self._format_file_size(it.size_bytes)
            lines.append(f"{icon} [{it.name}]({it.path}) — `{size_label}`")

        if not matches:
            lines.append(f"*No files found matching '{pattern}' in {folder_label}.*")
        elif len(matches) > 60:
            lines.append(f"\n*... and {len(matches) - 60} more items.*")

        summary = "\n".join(lines)
        result_data = {
            "type": "search_results",
            "pattern": pattern,
            "folder": str(folder) if folder else "all_roots",
            "count": len(matches),
            "files": [
                {
                    "name": it.name,
                    "path": it.path,
                    "is_directory": it.is_directory,
                    "size_bytes": it.size_bytes,
                    "size_formatted": "Folder" if it.is_directory else self._format_file_size(it.size_bytes),
                }
                for it in matches
            ],
        }

        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
            result_data=result_data,
        )

    def _handle_read_file(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        file_path = payload.get("file_path") or payload.get("path") or payload.get("source_path")
        if not file_path:
            raise ValueError("Missing required 'file_path' parameter.")

        result = self.tools.read_file_content(file_path)
        content_preview = result["content"]
        trunc_note = f"\n\n*(Preview truncated: total size {self._format_file_size(result['size_bytes'])})*" if result["truncated"] else ""
        summary = f"📄 **File Content: `{result['name']}`**\n\n```\n{content_preview}\n```{trunc_note}"

        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
            result_data={"type": "file_content", **result},
        )

    def _handle_move(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        src = payload.get("source_path")
        dest = payload.get("destination_path")
        overwrite = payload.get("overwrite", False)
        require_approval = payload.get("require_approval", True)

        if require_approval:
            approval = self.client.request_approval(
                task_id=task.id,
                action_type="file_move",
                description=f"Move '{src}' to '{dest}'",
                details={"source": src, "destination": dest, "overwrite": overwrite},
            )
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

    def _handle_open_file(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        file_path = payload.get("path") or payload.get("file_path")
        if not file_path:
            raise ValueError("Missing required 'file_path' or 'path' parameter.")
        reveal = payload.get("reveal", False)
        result = self.tools.open_file(file_path, reveal=reveal)
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=result.message,
            result_data={"type": "open_file", **result.model_dump()},
        )

    def _handle_rename(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        file_path = payload.get("file_path") or payload.get("path")
        new_name = payload.get("new_name")
        if not file_path or not new_name:
            raise ValueError("Missing required 'file_path' or 'new_name' parameter.")

        result = self.tools.rename_file(file_path, new_name)
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=result.message,
            result_data={"type": "rename_file", **result.model_dump()},
        )

    def _handle_delete(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        file_path = payload.get("file_path") or payload.get("path")
        if not file_path:
            raise ValueError("Missing required 'file_path' parameter.")
        permanent = payload.get("permanent", False)
        require_approval = payload.get("require_approval", False)

        if require_approval:
            approval = self.client.request_approval(
                task_id=task.id,
                action_type="file_delete",
                title=f"Approval needed: Delete '{file_path}'",
                description=f"Request to delete file: {file_path} (permanent={permanent})",
                metadata={"file_path": file_path, "permanent": permanent},
            )
            if approval.status == ApprovalStatus.PENDING:
                self.client.update_task(
                    task.id,
                    status=TaskStatus.AWAITING_APPROVAL,
                    result_summary=f"Waiting for approval to delete '{file_path}'",
                )
                return
            elif approval.status == ApprovalStatus.REJECTED:
                self.client.update_task(
                    task.id,
                    status=TaskStatus.FAILED,
                    error_message=f"File deletion was rejected: {approval.reason or 'User denied'}",
                )
                return

        result = self.tools.delete_file(file_path, permanent=permanent)
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=result.message,
            result_data={"type": "delete_file", **result.model_dump()},
        )

    # --- Desktop Action Handlers ---

    def _handle_system_telemetry(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        snapshot = self.telemetry.collect_telemetry()
        bat = f", Battery: {snapshot.battery_percent}%" if snapshot.battery_percent is not None else ""
        charging = " (Charging)" if snapshot.is_charging else ""
        summary = (
            f"System Telemetry: CPU: {snapshot.cpu_percent}%, RAM: {snapshot.memory_used_percent}% "
            f"({snapshot.memory_total_gb} GB){bat}{charging}, Windows: {len(snapshot.open_windows)}"
        )
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
        )

    def _handle_app_launch(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        app_name = payload.get("app_name")
        args = payload.get("arguments", [])
        if not app_name:
            raise ValueError("Missing required 'app_name' parameter.")

        res = self.apps.launch_app(app_name, arguments=args)
        status = TaskStatus.COMPLETED if res.status == "success" else TaskStatus.FAILED
        self.client.update_task(
            task.id,
            status=status,
            result_summary=res.message,
        )

    def _handle_app_close(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        target = payload.get("target")
        force = payload.get("force", False)
        require_approval = payload.get("require_approval", True)

        if not target:
            raise ValueError("Missing required 'target' parameter for app_close.")

        if require_approval:
            approval = self.client.request_approval(
                task_id=task.id,
                action_type="app_close",
                description=f"Terminate desktop application '{target}'",
                details={"target": target, "force": force},
            )
            resolved = self.client.poll_approval(approval.id, timeout_seconds=300.0)
            if resolved.status != ApprovalStatus.APPROVED:
                reason = resolved.rejection_reason or "App termination rejected by user."
                self.client.update_task(
                    task.id,
                    status=TaskStatus.FAILED,
                    error_message=f"Termination rejected: {reason}",
                )
                return

        res = self.apps.close_app(target, force=force)
        status = TaskStatus.COMPLETED if res.status == "success" else TaskStatus.FAILED
        self.client.update_task(
            task.id,
            status=status,
            result_summary=res.message,
        )

    def _handle_list_windows(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        windows = self.telemetry.get_open_windows()
        titles = [w.title for w in windows]
        summary = f"Active Windows ({len(titles)}): {', '.join(titles[:5])}" if titles else "No active desktop windows found."
        self.client.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result_summary=summary,
        )

    def _handle_allowlisted_command(self, task: TaskResponse, payload: Dict[str, Any]) -> None:
        cmd_str = payload.get("command")
        if not cmd_str:
            raise ValueError("Missing required 'command' parameter.")

        cmd_type = AllowlistedCommandType(cmd_str)
        res = self.scripts.execute_command(cmd_type, params=payload.get("params"))

        status = TaskStatus.COMPLETED if res.status == "success" else TaskStatus.FAILED
        self.client.update_task(
            task.id,
            status=status,
            result_summary=res.message,
        )


task_executor = TaskExecutor()
