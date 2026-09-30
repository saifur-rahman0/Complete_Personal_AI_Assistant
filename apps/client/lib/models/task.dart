class TaskItem {
  final String id;
  final String title;
  final String? description;
  final String status;
  final String priority;
  final String targetDevice;
  final Map<String, dynamic> payload;
  final String? resultSummary;
  final String? errorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;

  const TaskItem({
    required this.id,
    required this.title,
    this.description,
    required this.status,
    required this.priority,
    required this.targetDevice,
    this.payload = const {},
    this.resultSummary,
    this.errorMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory TaskItem.fromJson(Map<String, dynamic> json) {
    return TaskItem(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String?,
      status: json['status'] as String? ?? 'pending',
      priority: json['priority'] as String? ?? 'normal',
      targetDevice: json['target_device'] as String? ?? 'windows',
      payload: (json['payload'] as Map<String, dynamic>?) ?? {},
      resultSummary: json['result_summary'] as String?,
      errorMessage: json['error_message'] as String?,
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
    );
  }

  bool get isRunning => status == 'running';
  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
  bool get isAwaitingApproval => status == 'awaiting_approval';
  bool get isPending => status == 'pending';
}
