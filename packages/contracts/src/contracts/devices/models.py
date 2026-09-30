from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    ANDROID = "android"
    WINDOWS = "windows"
    WEB = "web"


class DevicePairingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DevicePairingInitRequest(BaseModel):
    device_id: str = Field(description="Unique device hardware or installation identifier")
    device_name: str = Field(description="Human-readable device name (e.g., 'Pixel 8 Pro')")
    device_type: DeviceType = Field(default=DeviceType.ANDROID, description="Device operating system/platform")
    client_public_key: Optional[str] = Field(default=None, description="Client public key or fingerprint for mutual authentication")


class DevicePairingInitResponse(BaseModel):
    pairing_session_id: str = Field(description="Temporary session ID for the pairing handshake")
    pin_code: str = Field(description="6-digit numeric pairing PIN code shown to user")
    expires_at: datetime = Field(description="Timestamp when the pairing PIN expires (e.g., 5 minutes)")


class DevicePairingConfirmRequest(BaseModel):
    pairing_session_id: str = Field(description="Pairing session ID from init step")
    pin_code: str = Field(description="6-digit PIN code entered by the user on the companion device")
    device_id: str = Field(description="Device ID completing the confirmation")
    client_public_key: Optional[str] = Field(default=None, description="Client key or challenge signature")


class DevicePairingConfirmResponse(BaseModel):
    device_id: str
    status: DevicePairingStatus
    auth_token: str = Field(description="Bearer token or shared secret for authenticated communication")
    message: str


class PairedDevice(BaseModel):
    device_id: str
    device_name: str
    device_type: DeviceType
    public_key: Optional[str] = None
    paired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
