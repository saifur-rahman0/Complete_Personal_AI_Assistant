class DevicePairingInitResult {
  final String pairingSessionId;
  final String pinCode;
  final DateTime expiresAt;

  DevicePairingInitResult({
    required this.pairingSessionId,
    required this.pinCode,
    required this.expiresAt,
  });

  factory DevicePairingInitResult.fromJson(Map<String, dynamic> json) {
    return DevicePairingInitResult(
      pairingSessionId: json['pairing_session_id'] as String,
      pinCode: json['pin_code'] as String,
      expiresAt: DateTime.parse(json['expires_at'] as String),
    );
  }
}

class PairedDeviceInfo {
  final String deviceId;
  final String deviceName;
  final String deviceType;
  final DateTime pairedAt;
  final DateTime lastActiveAt;
  final bool isActive;

  PairedDeviceInfo({
    required this.deviceId,
    required this.deviceName,
    required this.deviceType,
    required this.pairedAt,
    required this.lastActiveAt,
    required this.isActive,
  });

  factory PairedDeviceInfo.fromJson(Map<String, dynamic> json) {
    return PairedDeviceInfo(
      deviceId: json['device_id'] as String,
      deviceName: json['device_name'] as String,
      deviceType: (json['device_type'] as String?) ?? 'android',
      pairedAt: json['paired_at'] != null
          ? DateTime.parse(json['paired_at'] as String)
          : DateTime.now(),
      lastActiveAt: json['last_active_at'] != null
          ? DateTime.parse(json['last_active_at'] as String)
          : DateTime.now(),
      isActive: (json['is_active'] as bool?) ?? true,
    );
  }
}
