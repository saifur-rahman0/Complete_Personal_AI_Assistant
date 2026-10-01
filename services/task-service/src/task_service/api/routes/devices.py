from typing import List
from fastapi import APIRouter, HTTPException, status
from contracts.devices.models import (
    DeviceAutoPairRequest,
    DevicePairingConfirmRequest,
    DevicePairingConfirmResponse,
    DevicePairingInitRequest,
    DevicePairingInitResponse,
    PairedDevice,
)
from task_service.services.pairing_service import pairing_service

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("/pair/init", response_model=DevicePairingInitResponse, summary="Initiate device pairing handshake")
def initiate_pairing(req: DevicePairingInitRequest) -> DevicePairingInitResponse:
    return pairing_service.initiate_pairing(req)


@router.post("/pair/confirm", response_model=DevicePairingConfirmResponse, summary="Confirm device pairing with PIN")
def confirm_pairing(req: DevicePairingConfirmRequest) -> DevicePairingConfirmResponse:
    try:
        return pairing_service.confirm_pairing(req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/pair/auto", response_model=DevicePairingConfirmResponse, summary="Automatically pair companion on local network")
def auto_pair_device(req: DeviceAutoPairRequest) -> DevicePairingConfirmResponse:
    return pairing_service.auto_pair(
        device_id=req.device_id,
        device_name=req.device_name,
        device_type=req.device_type,
    )


@router.get("/paired", response_model=List[PairedDevice], summary="List all active paired companion devices")
def list_paired_devices() -> List[PairedDevice]:
    return pairing_service.list_paired_devices()


@router.delete("/{device_id}", summary="Revoke paired device access")
def revoke_device(device_id: str):
    success = pairing_service.revoke_device(device_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{device_id}' not found.")
    return {"status": "ok", "message": f"Device '{device_id}' access revoked."}
