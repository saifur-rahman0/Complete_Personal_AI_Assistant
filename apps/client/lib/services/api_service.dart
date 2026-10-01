import 'dart:convert';
import 'dart:io';
import 'package:personal_ai_assistant_apps/models/approval.dart';
import 'package:personal_ai_assistant_apps/models/reminder.dart';
import 'package:personal_ai_assistant_apps/models/route_result.dart';
import 'package:personal_ai_assistant_apps/models/sync_event.dart';
import 'package:personal_ai_assistant_apps/models/task.dart';

class ApiService {
  String gatewayBaseUrl;
  final String taskServiceBaseUrl;
  final String routerServiceBaseUrl;
  final String automationServiceBaseUrl;

  bool isPaired = false;
  String? authToken;

  static final List<String> candidateGatewayUrls = [
    'http://192.168.1.102:8000',
    'http://10.0.2.2:8000',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
  ];

  ApiService({
    String? gatewayUrl,
    String? taskServiceUrl,
    String? routerServiceUrl,
    String? automationServiceUrl,
  })  : gatewayBaseUrl = gatewayUrl ?? _defaultHost(8000),
        taskServiceBaseUrl = taskServiceUrl ?? _defaultHost(8001),
        routerServiceBaseUrl = routerServiceUrl ?? _defaultHost(8002),
        automationServiceBaseUrl = automationServiceUrl ?? _defaultHost(8003);

  void setGatewayUrl(String url) {
    var cleaned = url.trim();
    if (cleaned.endsWith('/')) {
      cleaned = cleaned.substring(0, cleaned.length - 1);
    }
    if (!cleaned.startsWith('http://') && !cleaned.startsWith('https://')) {
      cleaned = 'http://$cleaned';
    }
    gatewayBaseUrl = cleaned;
  }

  static String _defaultHost(int port) {
    // On Android devices, connect directly to the Laptop's Wi-Fi LAN IP
    if (Platform.isAndroid) {
      return 'http://192.168.1.102:$port';
    }
    return 'http://127.0.0.1:$port';
  }

  final HttpClient _client = HttpClient()
    ..connectionTimeout = const Duration(seconds: 4);

  Future<Map<String, dynamic>> _httpPost(String url, Map<String, dynamic> body) async {
    final uri = Uri.parse(url);
    final request = await _client.postUrl(uri);
    request.headers.set(HttpHeaders.contentTypeHeader, 'application/json');
    request.add(utf8.encode(jsonEncode(body)));
    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(responseBody) as Map<String, dynamic>;
    } else {
      throw HttpException('HTTP ${response.statusCode}: $responseBody', uri: uri);
    }
  }

  Future<dynamic> _httpGet(String url) async {
    final uri = Uri.parse(url);
    final request = await _client.getUrl(uri);
    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(responseBody);
    } else {
      throw HttpException('HTTP ${response.statusCode}: $responseBody', uri: uri);
    }
  }

  /// Sends user prompt to Decision Router to classify and auto-dispatch
  Future<RouteResult> dispatchPrompt(String prompt) async {
    final context = Platform.isAndroid ? 'android' : 'windows';
    try {
      // First attempt dispatch via Unified Gateway
      final data = await _httpPost(
        '$gatewayBaseUrl/api/v1/dispatch',
        {'prompt': prompt, 'device_context': context},
      );
      return RouteResult.fromDispatchJson(data);
    } catch (_) {
      try {
        // Fallback directly to Decision Router
        final data = await _httpPost(
          '$routerServiceBaseUrl/api/v1/router/dispatch',
          {'prompt': prompt, 'device_context': context},
        );
        return RouteResult.fromDispatchJson(data);
      } catch (e) {
        // Fallback: If router is unavailable, attempt direct task creation
        final taskData = await _httpPost(
          '$taskServiceBaseUrl/api/v1/tasks',
          {
            'title': prompt,
            'description': prompt,
            'target_device': 'windows',
            'priority': 'normal',
            'payload': {'action': 'organize_folder'},
          },
        );
        return RouteResult(
          intent: 'file_management',
          confidence: 0.8,
          targetService: 'windows-agent',
          createdTask: TaskItem.fromJson(taskData),
          message: 'Dispatched directly to Task Service.',
        );
      }
    }
  }

  /// Fetches all active tasks
  Future<List<TaskItem>> getTasks() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/tasks');
      final items = (data['items'] as List<dynamic>?) ?? [];
      return items.map((i) => TaskItem.fromJson(i as Map<String, dynamic>)).toList();
    } catch (_) {
      try {
        final data = await _httpGet('$taskServiceBaseUrl/api/v1/tasks');
        final items = (data['items'] as List<dynamic>?) ?? [];
        return items.map((i) => TaskItem.fromJson(i as Map<String, dynamic>)).toList();
      } catch (_) {
        return [];
      }
    }
  }

  /// Fetches all pending approval requests (used prominently on Android)
  Future<List<ApprovalItem>> getPendingApprovals() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/approvals?status=pending');
      final list = data as List<dynamic>? ?? [];
      return list.map((i) => ApprovalItem.fromJson(i as Map<String, dynamic>)).toList();
    } catch (_) {
      try {
        final data = await _httpGet('$taskServiceBaseUrl/api/v1/approvals?status=pending');
        final list = data as List<dynamic>? ?? [];
        return list.map((i) => ApprovalItem.fromJson(i as Map<String, dynamic>)).toList();
      } catch (_) {
        return [];
      }
    }
  }

  /// Resolves an approval request (Approve or Reject)
  Future<bool> resolveApproval(String approvalId, bool approved, {String? reason}) async {
    try {
      await _httpPost(
        '$gatewayBaseUrl/api/v1/approvals/$approvalId/resolve',
        {'approved': approved, 'reason': reason},
      );
      return true;
    } catch (_) {
      try {
        await _httpPost(
          '$taskServiceBaseUrl/api/v1/approvals/$approvalId/resolve',
          {'approved': approved, 'reason': reason},
        );
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  /// Fetches all active reminders
  Future<List<ReminderItem>> getReminders() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/reminders');
      final items = (data['items'] as List<dynamic>?) ?? [];
      return items.map((i) => ReminderItem.fromJson(i as Map<String, dynamic>)).toList();
    } catch (_) {
      try {
        final data = await _httpGet('$automationServiceBaseUrl/api/v1/reminders');
        final items = (data['items'] as List<dynamic>?) ?? [];
        return items.map((i) => ReminderItem.fromJson(i as Map<String, dynamic>)).toList();
      } catch (_) {
        return [];
      }
    }
  }

  /// Fetches currently due reminders
  Future<List<ReminderItem>> getDueReminders() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/reminders/due');
      final list = (data as List<dynamic>?) ?? [];
      return list.map((i) => ReminderItem.fromJson(i as Map<String, dynamic>)).toList();
    } catch (_) {
      try {
        final data = await _httpGet('$automationServiceBaseUrl/api/v1/reminders/due');
        final list = (data as List<dynamic>?) ?? [];
        return list.map((i) => ReminderItem.fromJson(i as Map<String, dynamic>)).toList();
      } catch (_) {
        return [];
      }
    }
  }

  /// Dismisses a due reminder
  Future<bool> dismissReminder(String reminderId) async {
    try {
      await _httpPost(
        '$gatewayBaseUrl/api/v1/reminders/$reminderId/dismiss',
        {},
      );
      return true;
    } catch (_) {
      try {
        await _httpPost(
          '$automationServiceBaseUrl/api/v1/reminders/$reminderId/dismiss',
          {},
        );
        return true;
      } catch (_) {
        return false;
      }
    }
  }

  int _consecutiveFailures = 0;
  bool _isAutoPairing = false;

  /// Checks if backend is reachable (Gateway preferred) and automatically syncs pairing
  Future<bool> checkHealth() async {
    // 1. Probe current gatewayBaseUrl
    if (await _probeUrl('$gatewayBaseUrl/health')) {
      _consecutiveFailures = 0;
      if (!isPaired && !_isAutoPairing) {
        _isAutoPairing = true;
        autoPair().whenComplete(() => _isAutoPairing = false);
      }
      return true;
    }

    _consecutiveFailures++;

    // 2. Only probe candidate URLs if current gateway failed repeatedly (prevents mobile lag)
    if (_consecutiveFailures >= 2) {
      for (final candidate in candidateGatewayUrls) {
        if (candidate == gatewayBaseUrl) continue;
        if (await _probeUrl('$candidate/health')) {
          gatewayBaseUrl = candidate;
          _consecutiveFailures = 0;
          if (!isPaired && !_isAutoPairing) {
            _isAutoPairing = true;
            autoPair().whenComplete(() => _isAutoPairing = false);
          }
          return true;
        }
      }
    }

    // 3. Fallback direct to task service
    try {
      final res = await _httpGet('$taskServiceBaseUrl/health');
      return res['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }

  Future<bool> _probeUrl(String url) async {
    try {
      final uri = Uri.parse(url);
      final request = await _client.getUrl(uri).timeout(const Duration(milliseconds: 900));
      final response = await request.close().timeout(const Duration(milliseconds: 900));
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
  }

  /// Fetches shared cross-device chat history from Gateway
  Future<List<Map<String, String>>> getChatHistory() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/chats');
      final list = (data as List<dynamic>?) ?? [];
      return list.map((item) {
        final map = item as Map<String, dynamic>;
        return {
          'role': (map['role'] as String?) ?? 'assistant',
          'text': (map['text'] as String?) ?? '',
        };
      }).toList();
    } catch (_) {
      return [];
    }
  }

  /// Initiates device pairing handshake with Windows workstation
  Future<Map<String, dynamic>?> initiatePairing({
    required String deviceId,
    required String deviceName,
    String deviceType = 'android',
  }) async {
    try {
      return await _httpPost(
        '$gatewayBaseUrl/api/v1/devices/pair/init',
        {
          'device_id': deviceId,
          'device_name': deviceName,
          'device_type': deviceType,
        },
      );
    } catch (_) {
      try {
        return await _httpPost(
          '$taskServiceBaseUrl/api/v1/devices/pair/init',
          {
            'device_id': deviceId,
            'device_name': deviceName,
            'device_type': deviceType,
          },
        );
      } catch (_) {
        return null;
      }
    }
  }

  /// Confirms device pairing with 6-digit PIN code
  Future<bool> confirmPairing({
    required String pairingSessionId,
    required String pinCode,
    required String deviceId,
  }) async {
    try {
      final res = await _httpPost(
        '$gatewayBaseUrl/api/v1/devices/pair/confirm',
        {
          'pairing_session_id': pairingSessionId,
          'pin_code': pinCode,
          'device_id': deviceId,
        },
      );
      if (res['status'] == 'confirmed') {
        isPaired = true;
        authToken = res['auth_token'] as String?;
        return true;
      }
      return false;
    } catch (_) {
      try {
        final res = await _httpPost(
          '$taskServiceBaseUrl/api/v1/devices/pair/confirm',
          {
            'pairing_session_id': pairingSessionId,
            'pin_code': pinCode,
            'device_id': deviceId,
          },
        );
        if (res['status'] == 'confirmed') {
          isPaired = true;
          authToken = res['auth_token'] as String?;
          return true;
        }
        return false;
      } catch (_) {
        return false;
      }
    }
  }

  /// Automatically pairs device on local network without PIN
  Future<bool> autoPair({
    String deviceId = 'android_companion_phone',
    String deviceName = 'Android Phone',
    String deviceType = 'android',
  }) async {
    try {
      final res = await _httpPost(
        '$gatewayBaseUrl/api/v1/devices/pair/auto',
        {
          'device_id': deviceId,
          'device_name': deviceName,
          'device_type': deviceType,
        },
      );
      if (res['status'] == 'confirmed') {
        isPaired = true;
        authToken = res['auth_token'] as String?;
        return true;
      }
      return false;
    } catch (_) {
      try {
        final res = await _httpPost(
          '$taskServiceBaseUrl/api/v1/devices/pair/auto',
          {
            'device_id': deviceId,
            'device_name': deviceName,
            'device_type': deviceType,
          },
        );
        if (res['status'] == 'confirmed') {
          isPaired = true;
          authToken = res['auth_token'] as String?;
          return true;
        }
        return false;
      } catch (_) {
        return false;
      }
    }
  }

  /// Fetches all active paired companion devices
  Future<List<Map<String, dynamic>>> getPairedDevices() async {
    try {
      final data = await _httpGet('$gatewayBaseUrl/api/v1/devices/paired');
      final list = (data as List<dynamic>?) ?? [];
      return list.cast<Map<String, dynamic>>();
    } catch (_) {
      try {
        final data = await _httpGet('$taskServiceBaseUrl/api/v1/devices/paired');
        final list = (data as List<dynamic>?) ?? [];
        return list.cast<Map<String, dynamic>>();
      } catch (_) {
        return [];
      }
    }
  }

  /// Syncs offline action batch with Gateway and fetches new events
  Future<SyncBatchResult?> syncBatch({
    required String deviceId,
    String? lastEventId,
    List<OfflineAction> offlineActions = const [],
  }) async {
    try {
      final data = await _httpPost(
        '$gatewayBaseUrl/api/v1/sync/batch',
        {
          'device_id': deviceId,
          'last_event_id': lastEventId,
          'offline_actions': offlineActions.map((a) => a.toJson()).toList(),
        },
      );
      return SyncBatchResult.fromJson(data);
    } catch (_) {
      return null;
    }
  }

  /// Fetches new sync events since watermark from Gateway
  Future<List<SyncEventItem>> fetchSyncEvents({String? lastEventId}) async {
    try {
      final url = lastEventId != null
          ? '$gatewayBaseUrl/api/v1/sync/events?last_event_id=$lastEventId'
          : '$gatewayBaseUrl/api/v1/sync/events';
      final data = await _httpGet(url);
      final list = (data as List<dynamic>?) ?? [];
      return list.map((e) => SyncEventItem.fromJson(e as Map<String, dynamic>)).toList();
    } catch (_) {
      return [];
    }
  }

  /// Opens or reveals a file/folder on the Windows workstation.
  Future<bool> openPath(String path, {bool reveal = true}) async {
    // 1. If running on Windows desktop natively, launch explorer directly
    if (Platform.isWindows) {
      try {
        if (reveal) {
          await Process.run('explorer.exe', ['/select,', path]);
        } else {
          await Process.run('explorer.exe', [path]);
        }
        return true;
      } catch (_) {
        // Fall back to gateway API
      }
    }

    // 2. Cross-device or fallback via Gateway endpoint
    try {
      await _httpPost(
        '$gatewayBaseUrl/api/v1/files/open',
        {'path': path, 'reveal': reveal},
      );
      return true;
    } catch (_) {
      return false;
    }
  }
}

final apiService = ApiService();

