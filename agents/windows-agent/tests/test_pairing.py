from datetime import datetime, timezone
import hashlib
import hmac
import pytest
from contracts.devices.models import (
    DevicePairingConfirmRequest,
    DevicePairingInitRequest,
    DevicePairingStatus,
    DeviceType,
)
from windows_agent.pairing.manager import DevicePairingManager


def test_pairing_handshake_lifecycle():
    manager = DevicePairingManager()

    # 1. Initiate pairing
    init_req = DevicePairingInitRequest(
        device_id="android-phone-001",
        device_name="Samsung Galaxy S24",
        device_type=DeviceType.ANDROID,
    )
    init_res = manager.initiate_pairing(init_req)

    assert len(init_res.pin_code) == 6
    assert init_res.pin_code.isdigit()
    assert init_res.pairing_session_id is not None

    # 2. Confirm pairing with invalid PIN
    bad_confirm = DevicePairingConfirmRequest(
        pairing_session_id=init_res.pairing_session_id,
        pin_code="000000",
        device_id="android-phone-001",
    )
    with pytest.raises(ValueError, match="Invalid pairing PIN"):
        manager.confirm_pairing(bad_confirm)

    # 3. Confirm pairing with valid PIN
    good_confirm = DevicePairingConfirmRequest(
        pairing_session_id=init_res.pairing_session_id,
        pin_code=init_res.pin_code,
        device_id="android-phone-001",
    )
    confirm_res = manager.confirm_pairing(good_confirm)
    assert confirm_res.status == DevicePairingStatus.CONFIRMED
    assert len(confirm_res.auth_token) == 64  # 32 bytes hex

    # 4. Check paired devices list
    paired = manager.list_paired_devices()
    assert len(paired) == 1
    assert paired[0].device_id == "android-phone-001"
    assert paired[0].device_name == "Samsung Galaxy S24"

    # 5. Authenticate signed request
    timestamp_str = datetime.now(timezone.utc).isoformat()
    body = '{"command":"system_telemetry"}'
    message = f"android-phone-001:{timestamp_str}:{body}".encode("utf-8")
    valid_sig = hmac.new(confirm_res.auth_token.encode("utf-8"), message, hashlib.sha256).hexdigest()

    assert manager.verify_request_signature("android-phone-001", timestamp_str, body, valid_sig) is True

    # 6. Tampered body fails verification
    assert manager.verify_request_signature("android-phone-001", timestamp_str, '{"command":"tampered"}', valid_sig) is False

    # 7. Revoke device
    assert manager.revoke_device("android-phone-001") is True
    assert len(manager.list_paired_devices()) == 0
    assert manager.verify_request_signature("android-phone-001", timestamp_str, body, valid_sig) is False
