import 'dart:io';
import 'package:flutter/material.dart';
import 'package:personal_ai_assistant_apps/services/api_service.dart';

class DeviceSyncDialog extends StatefulWidget {
  final VoidCallback onSyncCompleted;

  const DeviceSyncDialog({super.key, required this.onSyncCompleted});

  @override
  State<DeviceSyncDialog> createState() => _DeviceSyncDialogState();
}

class _DeviceSyncDialogState extends State<DeviceSyncDialog> {
  late TextEditingController _urlController;
  final TextEditingController _pinController = TextEditingController();

  bool _isTestingConnection = false;
  String? _connectionStatusMessage;
  bool _isConnectionSuccess = false;

  // Pairing state
  bool _isLoadingPairing = false;
  String? _activeSessionId;
  String? _generatedPin;
  String? _pairingMessage;
  bool _isPairingSuccess = false;
  List<Map<String, dynamic>> _pairedDevices = [];

  @override
  void initState() {
    super.initState();
    _urlController = TextEditingController(text: apiService.gatewayBaseUrl);
    _loadPairedDevices();
  }

  @override
  void dispose() {
    _urlController.dispose();
    _pinController.dispose();
    super.dispose();
  }

  Future<void> _loadPairedDevices() async {
    final devices = await apiService.getPairedDevices();
    if (mounted) {
      setState(() => _pairedDevices = devices);
    }
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTestingConnection = true;
      _connectionStatusMessage = null;
    });

    apiService.setGatewayUrl(_urlController.text);
    final stopwatch = Stopwatch()..start();
    final ok = await apiService.checkHealth();
    stopwatch.stop();

    if (!mounted) return;
    setState(() {
      _isTestingConnection = false;
      _isConnectionSuccess = ok;
      if (ok) {
        _connectionStatusMessage = 'Connected! Latency: ${stopwatch.elapsedMilliseconds} ms';
      } else {
        _connectionStatusMessage = 'Could not reach Gateway at ${_urlController.text}. Ensure scripts/run_local.py is running on PC.';
      }
    });

    if (ok) {
      widget.onSyncCompleted();
      _loadPairedDevices();
    }
  }

  Future<void> _generatePin() async {
    setState(() {
      _isLoadingPairing = true;
      _pairingMessage = null;
    });

    final res = await apiService.initiatePairing(
      deviceId: 'android_companion_phone',
      deviceName: 'Android Phone',
      deviceType: 'android',
    );

    if (!mounted) return;
    setState(() {
      _isLoadingPairing = false;
      if (res != null && res['pin_code'] != null) {
        _activeSessionId = res['pairing_session_id'] as String?;
        _generatedPin = res['pin_code'] as String?;
        _isPairingSuccess = true;
        _pairingMessage = 'PIN generated! Enter this 6-digit code on your phone:';
      } else {
        _pairingMessage = 'Failed to generate PIN. Check connection to Gateway.';
        _isPairingSuccess = false;
      }
    });
  }

  Future<void> _confirmPin() async {
    final pin = _pinController.text.trim();
    if (pin.length != 6) {
      setState(() {
        _pairingMessage = 'Please enter a valid 6-digit numeric PIN.';
        _isPairingSuccess = false;
      });
      return;
    }

    setState(() {
      _isLoadingPairing = true;
      _pairingMessage = null;
    });

    // If session ID isn't known, fetch active pairing session or use default
    final sessionId = _activeSessionId ?? 'session_default';
    final success = await apiService.confirmPairing(
      pairingSessionId: sessionId,
      pinCode: pin,
      deviceId: 'android_companion_phone',
    );

    if (!mounted) return;
    setState(() {
      _isLoadingPairing = false;
      _isPairingSuccess = success;
      if (success) {
        _pairingMessage = 'Success! Phone is authenticated and paired with Workstation.';
        _pinController.clear();
      } else {
        _pairingMessage = 'Pairing verification failed. Check that the PIN matches your PC.';
      }
    });

    if (success) {
      widget.onSyncCompleted();
      _loadPairedDevices();
    }
  }

  @override
  Widget build(BuildContext context) {
    final isAndroid = Platform.isAndroid;

    return Dialog(
      backgroundColor: const Color(0xFF161B26),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: Colors.cyanAccent.withValues(alpha: 0.2)),
      ),
      child: Container(
        padding: const EdgeInsets.all(24),
        constraints: const BoxConstraints(maxWidth: 520, maxHeight: 680),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Row(
                children: [
                  const Icon(Icons.sync_alt, color: Colors.cyanAccent, size: 28),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'Cross-Device Connect & Sync',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.grey),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                'Connect your phone and PC to sync commands, approvals, and reminders in real-time.',
                style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
              ),
              const Divider(color: Colors.white12, height: 28),

              // Section 1: Gateway URL Configuration
              const Text(
                'GATEWAY SERVER ADDRESS',
                style: TextStyle(
                  color: Colors.cyanAccent,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _urlController,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                      decoration: InputDecoration(
                        filled: true,
                        fillColor: const Color(0xFF0F121A),
                        hintText: 'http://192.168.1.102:8000',
                        hintStyle: TextStyle(color: Colors.grey.shade600),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(10),
                          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                        ),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  ElevatedButton(
                    onPressed: _isTestingConnection ? null : _testConnection,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.cyanAccent.shade700,
                      foregroundColor: Colors.black,
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: _isTestingConnection
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Text('Connect', style: TextStyle(fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Quick IP chips
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  ActionChip(
                    label: const Text('192.168.1.102 (Wi-Fi)'),
                    labelStyle: const TextStyle(fontSize: 11, color: Colors.cyanAccent),
                    backgroundColor: Colors.cyanAccent.withValues(alpha: 0.1),
                    onPressed: () {
                      _urlController.text = 'http://192.168.1.102:8000';
                      _testConnection();
                    },
                  ),
                  ActionChip(
                    label: const Text('127.0.0.1 (Localhost)'),
                    labelStyle: const TextStyle(fontSize: 11, color: Colors.grey),
                    backgroundColor: Colors.white.withValues(alpha: 0.05),
                    onPressed: () {
                      _urlController.text = 'http://127.0.0.1:8000';
                      _testConnection();
                    },
                  ),
                  ActionChip(
                    label: const Text('10.0.2.2 (Emulator)'),
                    labelStyle: const TextStyle(fontSize: 11, color: Colors.grey),
                    backgroundColor: Colors.white.withValues(alpha: 0.05),
                    onPressed: () {
                      _urlController.text = 'http://10.0.2.2:8000';
                      _testConnection();
                    },
                  ),
                ],
              ),

              if (_connectionStatusMessage != null) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: _isConnectionSuccess
                        ? Colors.teal.withValues(alpha: 0.15)
                        : Colors.red.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: _isConnectionSuccess ? Colors.tealAccent : Colors.redAccent,
                      width: 0.5,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _isConnectionSuccess ? Icons.check_circle : Icons.error_outline,
                        color: _isConnectionSuccess ? Colors.tealAccent : Colors.redAccent,
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _connectionStatusMessage!,
                          style: TextStyle(
                            color: _isConnectionSuccess ? Colors.tealAccent : Colors.redAccent,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              const Divider(color: Colors.white12, height: 28),

              // Section 2: Device Pairing & PIN Handshake
              Text(
                isAndroid ? 'PAIR WITH WORKSTATION' : 'PAIR YOUR PHONE (COMPANION)',
                style: const TextStyle(
                  color: Colors.cyanAccent,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.1,
                ),
              ),
              const SizedBox(height: 8),

              if (!isAndroid) ...[
                // Windows Workstation UI: Generate 6-Digit PIN
                Text(
                  'Generate a secure 6-digit PIN on this PC and enter it on your phone:',
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                ),
                const SizedBox(height: 12),
                if (_generatedPin == null)
                  ElevatedButton.icon(
                    onPressed: _isLoadingPairing ? null : _generatePin,
                    icon: const Icon(Icons.pin, color: Colors.black),
                    label: _isLoadingPairing
                        ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                        : const Text('Generate 6-Digit PIN', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black)),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.tealAccent,
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  )
                else ...[
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 20),
                    decoration: BoxDecoration(
                      color: Colors.cyanAccent.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.cyanAccent, width: 1.5),
                    ),
                    child: Center(
                      child: Text(
                        _generatedPin!,
                        style: const TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 8,
                          color: Colors.cyanAccent,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Open the Jarvis app on your phone, click Connect, and enter this PIN.',
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
                  ),
                ],
              ] else ...[
                // Android Phone UI: Enter PIN from PC
                Text(
                  'Enter the 6-digit PIN shown on your Windows PC to authenticate:',
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _pinController,
                        keyboardType: TextInputType.number,
                        maxLength: 6,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 6,
                          color: Colors.cyanAccent,
                        ),
                        decoration: InputDecoration(
                          counterText: '',
                          filled: true,
                          fillColor: const Color(0xFF0F121A),
                          hintText: '123456',
                          hintStyle: TextStyle(color: Colors.grey.shade700, letterSpacing: 6),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(10),
                            borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    ElevatedButton(
                      onPressed: _isLoadingPairing ? null : _confirmPin,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.tealAccent,
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      child: _isLoadingPairing
                          ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black))
                          : const Text('Pair Device', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ],

              if (_pairingMessage != null) ...[
                const SizedBox(height: 10),
                Text(
                  _pairingMessage!,
                  style: TextStyle(
                    color: _isPairingSuccess ? Colors.tealAccent : Colors.redAccent,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],

              // Paired devices list
              if (_pairedDevices.isNotEmpty) ...[
                const SizedBox(height: 16),
                const Text(
                  'PAIRED DEVICES',
                  style: TextStyle(
                    color: Colors.grey,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.0,
                  ),
                ),
                const SizedBox(height: 6),
                ..._pairedDevices.map((d) => Container(
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.04),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: [
                          Icon(
                            d['device_type'] == 'android' ? Icons.phone_android : Icons.computer,
                            color: Colors.cyanAccent,
                            size: 18,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              d['device_name'] ?? d['device_id'] ?? 'Device',
                              style: const TextStyle(color: Colors.white, fontSize: 13),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.teal.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Text('LINKED', style: TextStyle(color: Colors.tealAccent, fontSize: 10, fontWeight: FontWeight.bold)),
                          ),
                        ],
                      ),
                    )),
              ],

              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () {
                    widget.onSyncCompleted();
                    Navigator.of(context).pop();
                  },
                  icon: const Icon(Icons.done, color: Colors.black),
                  label: const Text('Done', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.black)),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.cyanAccent,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
