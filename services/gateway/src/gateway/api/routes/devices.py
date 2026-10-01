from fastapi import APIRouter, HTTPException, Request, status
import httpx
from gateway.audit import audit_logger
from gateway.config import settings

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("/pair/init", summary="Initiate device pairing handshake")
async def initiate_pairing(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
            resp = await client.post("/api/v1/devices/pair/init", json=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/pair/confirm", summary="Confirm device pairing with PIN")
async def confirm_pairing(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
            resp = await client.post("/api/v1/devices/pair/confirm", json=body)
            resp.raise_for_status()
            data = resp.json()

            audit_logger.record(
                action="device_pairing_confirmed",
                actor=body.get("device_id") or "unknown",
                target=f"session:{body.get('pairing_session_id')}",
                status="SUCCESS",
                correlation_id=request.headers.get("X-Correlation-ID"),
                details={"device_id": body.get("device_id")},
            )
            return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/pair/auto", summary="Automatically pair companion device on local network")
async def auto_pair(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
            resp = await client.post("/api/v1/devices/pair/auto", json=body)
            resp.raise_for_status()
            data = resp.json()

            audit_logger.record(
                action="device_auto_paired",
                actor=body.get("device_id") or "unknown",
                target=f"device:{body.get('device_id')}",
                status="SUCCESS",
                correlation_id=request.headers.get("X-Correlation-ID"),
                details={"device_name": body.get("device_name")},
            )
            return data
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/paired", summary="List paired devices")
async def list_paired_devices():
    try:
        async with httpx.AsyncClient(base_url=settings.TASK_SERVICE_URL, timeout=5.0) as client:
            resp = await client.get("/api/v1/devices/paired")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
