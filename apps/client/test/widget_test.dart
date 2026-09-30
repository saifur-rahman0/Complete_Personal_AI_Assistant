import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:personal_ai_assistant_apps/main.dart';
import 'package:personal_ai_assistant_apps/widgets/device_sync_dialog.dart';
import 'package:personal_ai_assistant_apps/models/approval.dart';
import 'package:personal_ai_assistant_apps/models/device_pairing.dart';
import 'package:personal_ai_assistant_apps/models/reminder.dart';
import 'package:personal_ai_assistant_apps/models/sync_event.dart';
import 'package:personal_ai_assistant_apps/models/system_telemetry.dart';
import 'package:personal_ai_assistant_apps/models/task.dart';


void main() {
  test('TaskItem and ApprovalItem serialization test', () {
    final task = TaskItem.fromJson({
      'id': 'task-101',
      'title': 'Organize Downloads',
      'status': 'awaiting_approval',
      'priority': 'high',
      'target_device': 'windows',
      'payload': {'action': 'organize_folder'},
      'created_at': DateTime.now().toIso8601String(),
      'updated_at': DateTime.now().toIso8601String(),
    });

    expect(task.id, 'task-101');
    expect(task.title, 'Organize Downloads');
    expect(task.isAwaitingApproval, isTrue);

    final approval = ApprovalItem.fromJson({
      'id': 'appr-202',
      'task_id': 'task-101',
      'action_type': 'folder_organize',
      'description': 'Move 14 files into category folders',
      'status': 'pending',
      'created_at': DateTime.now().toIso8601String(),
    });

    expect(approval.id, 'appr-202');
    expect(approval.isPending, isTrue);
    expect(approval.actionType, 'folder_organize');

    final reminder = ReminderItem.fromJson({
      'id': 'rem-303',
      'title': 'Call dentist',
      'trigger_at': DateTime.now().add(const Duration(minutes: 30)).toIso8601String(),
      'status': 'pending',
      'target_device': 'android',
    });

    expect(reminder.id, 'rem-303');
    expect(reminder.title, 'Call dentist');
    expect(reminder.isPending, isTrue);
    expect(reminder.targetDevice, 'android');
  });

  test('DevicePairing and SystemTelemetry serialization test', () {
    final pairing = DevicePairingInitResult.fromJson({
      'pairing_session_id': 'sess-999',
      'pin_code': '482910',
      'expires_at': DateTime.now().add(const Duration(minutes: 5)).toIso8601String(),
    });

    expect(pairing.pairingSessionId, 'sess-999');
    expect(pairing.pinCode, '482910');

    final device = PairedDeviceInfo.fromJson({
      'device_id': 'phone-01',
      'device_name': 'Samsung Galaxy',
      'device_type': 'android',
      'is_active': true,
    });

    expect(device.deviceId, 'phone-01');
    expect(device.deviceName, 'Samsung Galaxy');
    expect(device.isActive, isTrue);

    final telemetry = SystemTelemetryData.fromJson({
      'cpu_percent': 24.5,
      'memory_used_percent': 62.0,
      'memory_total_gb': 15.8,
      'battery_percent': 85,
      'is_charging': true,
      'open_windows': [
        {'title': 'Notepad', 'handle': 1234},
      ],
    });

    expect(telemetry.cpuPercent, 24.5);
    expect(telemetry.memoryUsedPercent, 62.0);
    expect(telemetry.batteryPercent, 85);
    expect(telemetry.isCharging, isTrue);
    expect(telemetry.openWindows.length, 1);
    expect(telemetry.openWindows.first.title, 'Notepad');
  });

  test('SyncEventItem and SyncBatchResult serialization test', () {
    final syncEvent = SyncEventItem.fromJson({
      'event_id': 'evt_000001',
      'event_type': 'task.created',
      'device_id': 'device-pixel-8',
      'payload': {'task_id': 'task-999', 'status': 'created'},
      'correlation_id': 'corr-abc-123',
      'timestamp': DateTime.now().toIso8601String(),
    });

    expect(syncEvent.eventId, 'evt_000001');
    expect(syncEvent.eventType, 'task.created');
    expect(syncEvent.payload['task_id'], 'task-999');

    final action = OfflineAction(
      actionId: 'act-001',
      actionType: 'resolve_approval',
      payload: {'approval_id': 'appr-123', 'approved': true},
      queuedAt: DateTime.now(),
    );
    expect(action.actionId, 'act-001');
    expect(action.toJson()['action_type'], 'resolve_approval');

    final batchResult = SyncBatchResult.fromJson({
      'events': [
        {
          'event_id': 'evt_000001',
          'event_type': 'task.created',
          'timestamp': DateTime.now().toIso8601String(),
        }
      ],
      'processed_action_ids': ['act-001'],
      'latest_event_id': 'evt_000001',
      'server_time': DateTime.now().toIso8601String(),
    });

    expect(batchResult.events.length, 1);
    expect(batchResult.processedActionIds, contains('act-001'));
    expect(batchResult.latestEventId, 'evt_000001');
  });

  testWidgets('JarvisAssistantApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const JarvisAssistantApp());
    expect(find.text('Jarvis Assistant'), findsOneWidget);
  });

  testWidgets('DeviceSyncDialog smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const MaterialApp(
      home: Scaffold(
        body: DeviceSyncDialog(onSyncCompleted: _noop),
      ),
    ));
    expect(find.text('Cross-Device Connect & Sync'), findsOneWidget);
    expect(find.text('GATEWAY SERVER ADDRESS'), findsOneWidget);
  });
}

void _noop() {}

