class ReminderItem {
  final String id;
  final String title;
  final String? description;
  final DateTime triggerAt;
  final String status;
  final String targetDevice;
  final Map<String, dynamic> metadata;
  final DateTime createdAt;

  ReminderItem({
    required this.id,
    required this.title,
    this.description,
    required this.triggerAt,
    required this.status,
    required this.targetDevice,
    this.metadata = const {},
    required this.createdAt,
  });

  bool get isDue => status.toLowerCase() == 'due';
  bool get isPending => status.toLowerCase() == 'pending';
  bool get isDismissed => status.toLowerCase() == 'dismissed';

  factory ReminderItem.fromJson(Map<String, dynamic> json) {
    return ReminderItem(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      triggerAt: DateTime.parse(json['trigger_at'] as String),
      status: (json['status'] as String?) ?? 'pending',
      targetDevice: (json['target_device'] as String?) ?? 'any',
      metadata: (json['metadata'] as Map<String, dynamic>?) ?? {},
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : DateTime.now(),
    );
  }
}
