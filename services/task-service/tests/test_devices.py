import pytest
from fastapi.testclient import TestClient
from task_service.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_device_pairing_api_flow(client):
    # 1. Initiate pairing
    init_res = client.post(
        "/api/v1/devices/pair/init",
        json={
            "device_id": "phone-test-100",
            "device_name": "Test Android Companion",
            "device_type": "android",
        },
    )
    assert init_res.status_code == 200
    data = init_res.json()
    assert "pin_code" in data
    assert len(data["pin_code"]) == 6
    session_id = data["pairing_session_id"]
    pin_code = data["pin_code"]

    # 2. Confirm pairing with wrong PIN
    bad_confirm = client.post(
        "/api/v1/devices/pair/confirm",
        json={
            "pairing_session_id": session_id,
            "pin_code": "000000",
            "device_id": "phone-test-100",
        },
    )
    assert bad_confirm.status_code == 400
    assert "Invalid pairing PIN" in bad_confirm.json()["detail"]

    # 3. Confirm pairing with correct PIN
    good_confirm = client.post(
        "/api/v1/devices/pair/confirm",
        json={
            "pairing_session_id": session_id,
            "pin_code": pin_code,
            "device_id": "phone-test-100",
        },
    )
    assert good_confirm.status_code == 200
    confirm_data = good_confirm.json()
    assert confirm_data["status"] == "confirmed"
    assert "auth_token" in confirm_data

    # 4. List paired devices
    list_res = client.get("/api/v1/devices/paired")
    assert list_res.status_code == 200
    devices = list_res.json()
    assert len(devices) >= 1
    assert any(d["device_id"] == "phone-test-100" for d in devices)

    # 5. Revoke paired device
    delete_res = client.delete("/api/v1/devices/phone-test-100")
    assert delete_res.status_code == 200
    assert delete_res.json()["status"] == "ok"


def test_auto_pair_device(client):
    res = client.post(
        "/api/v1/devices/pair/auto",
        json={
            "device_id": "phone-auto-001",
            "device_name": "Living Room Android",
            "device_type": "android",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "confirmed"
    assert "auth_token" in data

    # Verify device is immediately listed as paired
    list_res = client.get("/api/v1/devices/paired")
    assert list_res.status_code == 200
    devices = list_res.json()
    assert any(d["device_id"] == "phone-auto-001" for d in devices)


def test_confirm_pairing_by_pin_only(client):
    init_res = client.post(
        "/api/v1/devices/pair/init",
        json={
            "device_id": "phone-pin-only",
            "device_name": "Companion Phone",
            "device_type": "android",
        },
    )
    pin = init_res.json()["pin_code"]

    # Confirm using only PIN without knowing the session UUID
    confirm_res = client.post(
        "/api/v1/devices/pair/confirm",
        json={
            "pin_code": pin,
            "device_id": "phone-pin-only",
        },
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"

