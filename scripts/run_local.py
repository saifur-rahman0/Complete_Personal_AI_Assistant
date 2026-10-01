"""
AI Workforce — Local Multi-Service Development Runner.
Starts all core microservices and the Windows Agent background worker together.

Services launched:
  1. gateway:            http://localhost:8000 (Unified API Gateway & Sync Stream)
  2. task-service:       http://localhost:8001 (Task & Approval Management)
  3. decision-router:    http://localhost:8002 (System One Classifier & Dispatcher)
  4. automation-service: http://localhost:8003 (Scheduled Reminders & Memory)
  5. web-research:       http://localhost:8004 (SSRF-Protected Web Scraping & Research)
  6. windows-agent:      Background worker polling task-service on port 8001
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = sys.executable


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("$env:"):
                    line = line[5:].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
    except Exception as e:
        print(f"Warning: could not read {env_path}: {e}")


_load_env_file(ROOT_DIR / ".env")

SERVICES = [
    {
        "name": "gateway",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "gateway.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "info",
        ],
        "cwd": ROOT_DIR / "services" / "gateway",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'services' / 'gateway' / 'src'}",
            "TASK_SERVICE_URL": "http://127.0.0.1:8001",
            "ROUTER_SERVICE_URL": "http://127.0.0.1:8002",
            "AUTOMATION_SERVICE_URL": "http://127.0.0.1:8003",
            "WEB_RESEARCH_SERVICE_URL": "http://127.0.0.1:8004",
        },
    },
    {
        "name": "task-service",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "task_service.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8001",
            "--log-level",
            "info",
        ],
        "cwd": ROOT_DIR / "services" / "task-service",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'services' / 'task-service' / 'src'}",
        },
    },
    {
        "name": "decision-router",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "decision_router.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8002",
            "--log-level",
            "info",
        ],
        "cwd": ROOT_DIR / "services" / "decision-router",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'services' / 'decision-router' / 'src'}",
            "TASK_SERVICE_URL": "http://127.0.0.1:8001",
            "AUTOMATION_SERVICE_URL": "http://127.0.0.1:8003",
            "WEB_RESEARCH_SERVICE_URL": "http://127.0.0.1:8004",
        },
    },
    {
        "name": "automation-service",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "automation_service.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8003",
            "--log-level",
            "info",
        ],
        "cwd": ROOT_DIR / "services" / "automation-service",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'services' / 'automation-service' / 'src'}",
            "TASK_SERVICE_URL": "http://127.0.0.1:8001",
        },
    },
    {
        "name": "web-research",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "uvicorn",
            "web_research.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8004",
            "--log-level",
            "info",
        ],
        "cwd": ROOT_DIR / "services" / "web-research",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'services' / 'web-research' / 'src'}",
        },
    },
    {
        "name": "windows-agent",
        "cmd": [
            PYTHON_EXE,
            "-m",
            "windows_agent.worker",
        ],
        "cwd": ROOT_DIR / "agents" / "windows-agent",
        "env": {
            "PYTHONPATH": f"{ROOT_DIR / 'packages' / 'contracts' / 'src'};{ROOT_DIR / 'agents' / 'windows-agent' / 'src'}",
            "TASK_SERVICE_URL": "http://127.0.0.1:8001",
        },
    },
]


def main():
    print("=" * 60)
    print(" Personal AI Assistant — Starting Local Services")
    print("=" * 60)

    processes = []

    def shutdown(signum=None, frame=None):
        print("\nStopping all services...")
        for proc, name in processes:
            print(f"Terminating {name} (PID: {proc.pid})...")
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        print("All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    for svc in SERVICES:
        name = svc["name"]
        env = os.environ.copy()
        env.update(svc["env"])
        print(f"--> Starting {name}...")

        proc = subprocess.Popen(
            svc["cmd"],
            cwd=str(svc["cwd"]),
            env=env,
        )
        processes.append((proc, name))
        time.sleep(1.0)

    import socket
    def _get_lan_ip() -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    lan_ip = _get_lan_ip()

    print("\n" + "=" * 60)
    print(" All services running:")
    print("   - Gateway (Workstation):  http://127.0.0.1:8000")
    print(f"   - Gateway (Phone Wi-Fi):  http://{lan_ip}:8000")
    print("   - Task Service:           http://127.0.0.1:8001")
    print("   - Decision Router:        http://127.0.0.1:8002")
    print("   - Automation Service:     http://127.0.0.1:8003")
    print("   - Web Research:           http://127.0.0.1:8004")
    print("   - Windows Agent:          Active (polling port 8001)")
    gemini_model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    llm_provider = (
        f"Google Gemini ({gemini_model_name}) (Online, Instant)"
        if os.environ.get("GEMINI_API_KEY")
        else (
            "Groq Cloud Llama 3.3 (Online, Instant)"
            if os.environ.get("GROQ_API_KEY")
            else "Ollama qwen2.5:7b (Local Fallback)"
        )
    )
    print(f"   - Conversational LLM:     {llm_provider}")
    print("   - Flutter Client:         Launch via 'flutter run' in apps/client")
    print("   - Device Pairing:         Zero-PIN Auto-Pairing Active on Wi-Fi")
    print(" Press Ctrl+C to terminate all services.")
    print("=" * 60 + "\n")

    try:
        while True:
            for proc, name in processes:
                poll = proc.poll()
                if poll is not None:
                    print(f"WARNING: Service {name} exited unexpectedly with code {poll}!")
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
