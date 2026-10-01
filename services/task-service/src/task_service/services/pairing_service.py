from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import logging
import secrets
from typing import Dict, List, Optional
import uuid

from contracts.devices.models import (
    DevicePairingConfirmRequest,
    DevicePairingConfirmResponse,
    DevicePairingInitRequest,
    DevicePairingInitResponse,
    DevicePairingStatus,
    DeviceType,
    PairedDevice,
)

logger = logging.getLogger("task_service.pairing")


class PairingSession:
    def __init__(
        self,
        session_id: str,
        pin_code: str,
        device_id: str,
        device_name: str,
        device_type: DeviceType,
        client_public_key: Optional[str],
        expires_at: datetime,
    ) -> None:
        self.session_id = session_id
        self.pin_code = pin_code
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.client_public_key = client_public_key
        self.expires_at = expires_at
        self.status = DevicePairingStatus.PENDING


class DevicePairingService:
    def __init__(self, pin_ttl_minutes: int = 5) -> None:
        self.pin_ttl_minutes = pin_ttl_minutes
        self._active_sessions: Dict[str, PairingSession] = {}
        self._paired_devices: Dict[str, PairedDevice] = {}
        self._device_secrets: Dict[str, str] = {}

    def initiate_pairing(self, req: DevicePairingInitRequest) -> DevicePairingInitResponse:
        session_id = str(uuid.uuid4())
        pin_code = str(secrets.randbelow(900000) + 100000)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.pin_ttl_minutes)

        session = PairingSession(
            session_id=session_id,
            pin_code=pin_code,
            device_id=req.device_id,
            device_name=req.device_name,
            device_type=req.device_type,
            client_public_key=req.client_public_key,
            expires_at=expires_at,
        )
        self._active_sessions[session_id] = session

        logger.info(
            f"Device pairing initiated for '{req.device_name}' (ID: {req.device_id}). "
            f"PIN: {pin_code} (Session: {session_id})"
        )

        return DevicePairingInitResponse(
            pairing_session_id=session_id,
            pin_code=pin_code,
            expires_at=expires_at,
        )

    def confirm_pairing(self, req: DevicePairingConfirmRequest) -> DevicePairingConfirmResponse:
        session = None
        # 1. Lookup by session ID if valid
        if req.pairing_session_id and req.pairing_session_id in self._active_sessions:
            session = self._active_sessions[req.pairing_session_id]

        # 2. If not found by ID or session_default, look up by matching PIN among active sessions
        if not session and req.pin_code:
            clean_pin = req.pin_code.strip()
            for s in self._active_sessions.values():
                if hmac.compare_digest(s.pin_code, clean_pin):
                    session = s
                    break

        now = datetime.now(timezone.utc)

        if not session:
            raise ValueError(f"Pairing PIN '{req.pin_code}' does not match any active pairing session.")

        if now > session.expires_at:
            session.status = DevicePairingStatus.EXPIRED
            raise ValueError("Pairing PIN has expired. Please initiate a new pairing session.")

        if not hmac.compare_digest(session.pin_code, req.pin_code.strip()):
            session.status = DevicePairingStatus.REJECTED
            raise ValueError("Invalid pairing PIN code provided.")

        shared_secret = secrets.token_hex(32)
        device_id = req.device_id or session.device_id
        device_name = session.device_name or "Android Phone"
        device_type = session.device_type or DeviceType.ANDROID

        paired_device = PairedDevice(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            public_key=req.client_public_key or session.client_public_key,
            paired_at=now,
            last_active_at=now,
            is_active=True,
        )

        self._paired_devices[device_id] = paired_device
        self._device_secrets[device_id] = shared_secret
        session.status = DevicePairingStatus.CONFIRMED

        logger.info(f"Successfully paired device '{device_name}' (ID: {device_id}).")

        return DevicePairingConfirmResponse(
            device_id=device_id,
            status=DevicePairingStatus.CONFIRMED,
            auth_token=shared_secret,
            message="Device successfully paired and authenticated.",
        )

    def auto_pair(
        self,
        device_id: str = "android_companion_phone",
        device_name: str = "Android Phone",
        device_type: DeviceType = DeviceType.ANDROID,
    ) -> DevicePairingConfirmResponse:
        """Instantly pairs a companion device on the local network without PIN friction."""
        now = datetime.now(timezone.utc)
        shared_secret = secrets.token_hex(32)

        paired_device = PairedDevice(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
            public_key=None,
            paired_at=now,
            last_active_at=now,
            is_active=True,
        )

        self._paired_devices[device_id] = paired_device
        self._device_secrets[device_id] = shared_secret

        logger.info(f"Auto-paired device on local network: '{device_name}' (ID: {device_id}).")

        return DevicePairingConfirmResponse(
            device_id=device_id,
            status=DevicePairingStatus.CONFIRMED,
            auth_token=shared_secret,
            message="Device automatically paired on local network.",
        )

    def list_paired_devices(self) -> List[PairedDevice]:
        return [d for d in self._paired_devices.values() if d.is_active]

    def revoke_device(self, device_id: str) -> bool:
        if device_id in self._paired_devices:
            self._paired_devices[device_id].is_active = False
            self._device_secrets.pop(device_id, None)
            return True
        return False


pairing_service = DevicePairingService()
