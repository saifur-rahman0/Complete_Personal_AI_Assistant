# Windows Agent Worker (`agents/windows-agent`)

The Windows Agent runs as a background worker on your Windows laptop. It communicates with the backend via outbound HTTP/WebSocket connections to safely execute authorized system tasks (such as folder organization and file searches) without exposing open inbound ports.

## Key Capabilities
- **Strict Path Allowlisting:** Operations are strictly confined to permitted user directories (e.g. `Downloads`, `Documents`, `Desktop`). Access to Windows system paths (`C:\Windows`, `C:\Program Files`) is strictly blocked.
- **Path Traversal Defense:** Defends against `..` escapes, symlink redirection, and unintended drive traversal.
- **Human Approval Enforcement:** Any moving, modifying, or bulk restructuring operation requests human authorization and waits until approved before altering any files on disk.
- **Safe Dry-Run Previews:** Folder reorganization previews changes before any actions are taken.

## Running Locally
```powershell
$env:PYTHONPATH="packages/contracts/src;agents/windows-agent/src"
.venv\Scripts\python -m windows_agent.worker
```
