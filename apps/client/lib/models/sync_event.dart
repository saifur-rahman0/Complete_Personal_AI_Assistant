class SyncEventItem {
  final String eventId;
  final String eventType;
  final String? deviceId;
  final Map<String, dynamic> payload;
  final String? correlationId;
  final DateTime timestamp;

  const SyncEventItem({
    required this.eventId,
    required this.eventType,
    this.deviceId,
    this.payload = const {},
    this.correlationId,
    required this.timestamp,
  });

  factory SyncEventItem.fromJson(Map<String, dynamic> json) {
    return SyncEventItem(
      eventId: json['event_id'] as String,
      eventType: json['event_type'] as String,
      deviceId: json['device_id'] as String?,
      payload: (json['payload'] as Map<String, dynamic>?) ?? {},
      correlationId: json['correlation_id'] as String?,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now(),
    );
  }
}

class OfflineAction {
  final String actionId;
  final String actionType;
  final Map<String, dynamic> payload;
  final DateTime queuedAt;

  const OfflineAction({
    required this.actionId,
    required this.actionType,
    this.payload = const {},
    required this.queuedAt,
  });

  Map<String, dynamic> toJson() => {
        'action_id': actionId,
        'action_type': actionType,
        'payload': payload,
        'queued_at': queuedAt.toIso8601String(),
      };
}

class SyncBatchResult {
  final List<SyncEventItem> events;
  final List<String> processedActionIds;
  final String? latestEventId;
  final DateTime serverTime;

  const SyncBatchResult({
    required this.events,
    required this.processedActionIds,
    this.latestEventId,
    required this.serverTime,
  });

  factory SyncBatchResult.fromJson(Map<String, dynamic> json) {
    final rawEvents = (json['events'] as List<dynamic>?) ?? [];
    final rawProcessed = (json['processed_action_ids'] as List<dynamic>?) ?? [];
    return SyncBatchResult(
      events: rawEvents.map((e) => SyncEventItem.fromJson(e as Map<String, dynamic>)).toList(),
      processedActionIds: rawProcessed.map((p) => p.toString()).toList(),
      latestEventId: json['latest_event_id'] as String?,
      serverTime: DateTime.tryParse(json['server_time'] as String? ?? '') ?? DateTime.now(),
    );
  }
}
