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

logger = logging.getLogger("windows_agent.pairing")


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


class DevicePairingManager:
    """
    Manages zero-trust cryptographic device pairing between mobile devices (Android)
    and the host Windows workstation. Enforces 6-digit numeric verification PIN and
    subsequent HMAC-SHA256 authenticated request signing.
    """

    def __init__(self, pin_ttl_minutes: int = 5) -> None:
        self.pin_ttl_minutes = pin_ttl_minutes
        self._active_sessions: Dict[str, PairingSession] = {}
        self._paired_devices: Dict[str, PairedDevice] = {}
        self._device_secrets: Dict[str, str] = {}

    def initiate_pairing(self, req: DevicePairingInitRequest) -> DevicePairingInitResponse:
        """Starts a pairing handshake session and issues a 6-digit PIN."""
        session_id = str(uuid.uuid4())
        # Cryptographically secure 6-digit PIN (100000 - 999999)
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
            f"Initiated device pairing for '{req.device_name}' (ID: {req.device_id}). "
            f"Verification PIN: {pin_code} (Session: {session_id})"
        )

        return DevicePairingInitResponse(
            pairing_session_id=session_id,
            pin_code=pin_code,
            expires_at=expires_at,
        )

    def confirm_pairing(self, req: DevicePairingConfirmRequest) -> DevicePairingConfirmResponse:
        """Validates the 6-digit PIN and completes mutual device pairing."""
        session = self._active_sessions.get(req.pairing_session_id)
        now = datetime.now(timezone.utc)

        if not session:
            raise ValueError(f"Pairing session '{req.pairing_session_id}' not found.")

        if now > session.expires_at:
            session.status = DevicePairingStatus.EXPIRED
            raise ValueError("Pairing PIN has expired. Please initiate a new pairing session.")

        if session.device_id != req.device_id:
            raise ValueError(f"Device ID mismatch for session '{req.pairing_session_id}'.")

        # Constant-time PIN comparison
        if not hmac.compare_digest(session.pin_code, req.pin_code.strip()):
            session.status = DevicePairingStatus.REJECTED
            raise ValueError("Invalid pairing PIN code provided.")

        # Pairing successful: generate high-entropy shared secret for HMAC authentication
        shared_secret = secrets.token_hex(32)
        paired_device = PairedDevice(
            device_id=session.device_id,
            device_name=session.device_name,
            device_type=session.device_type,
            public_key=req.client_public_key or session.client_public_key,
            paired_at=now,
            last_active_at=now,
            is_active=True,
        )

        self._paired_devices[session.device_id] = paired_device
        self._device_secrets[session.device_id] = shared_secret
        session.status = DevicePairingStatus.CONFIRMED

        logger.info(f"Successfully paired device '{session.device_name}' (ID: {session.device_id}).")

        return DevicePairingConfirmResponse(
            device_id=session.device_id,
            status=DevicePairingStatus.CONFIRMED,
            auth_token=shared_secret,
            message="Device successfully paired and authenticated.",
        )

    def verify_request_signature(
        self,
        device_id: str,
        timestamp_str: str,
        body: str,
        signature: str,
    ) -> bool:
        """
        Validates HMAC-SHA256 signature and timestamp freshness on incoming companion requests.
        Protects against spoofing and replay attacks.
        """
        secret = self._device_secrets.get(device_id)
        if not secret:
            logger.warning(f"Signature check failed: Device '{device_id}' is not paired.")
            return False

        # Replay attack protection: ensure request is within 5 minutes
        try:
            req_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if abs((now - req_time).total_seconds()) > 300.0:
                logger.warning(f"Signature check rejected: Expired timestamp from device '{device_id}'.")
                return False
        except Exception:
            return False

        message = f"{device_id}:{timestamp_str}:{body}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

        is_valid = hmac.compare_digest(expected_sig, signature)
        if is_valid:
            # Update last active timestamp
            if device_id in self._paired_devices:
                self._paired_devices[device_id].last_active_at = datetime.now(timezone.utc)
        return is_valid

    def list_paired_devices(self) -> List[PairedDevice]:
        """Returns list of currently paired devices."""
        return [d for d in self._paired_devices.values() if d.is_active]

    def revoke_device(self, device_id: str) -> bool:
        """Revokes a paired device and deletes its authentication secret."""
        if device_id in self._paired_devices:
            self._paired_devices[device_id].is_active = False
            self._device_secrets.pop(device_id, None)
            logger.info(f"Revoked paired device '{device_id}'.")
            return True
        return False


pairing_manager = DevicePairingManager()
