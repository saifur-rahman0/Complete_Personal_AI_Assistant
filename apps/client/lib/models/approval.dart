class ApprovalItem {
  final String id;
  final String taskId;
  final String actionType;
  final String description;
  final Map<String, dynamic> details;
  final String status;
  final DateTime createdAt;
  final DateTime? resolvedAt;
  final String? rejectionReason;

  const ApprovalItem({
    required this.id,
    required this.taskId,
    required this.actionType,
    required this.description,
    this.details = const {},
    required this.status,
    required this.createdAt,
    this.resolvedAt,
    this.rejectionReason,
  });

  factory ApprovalItem.fromJson(Map<String, dynamic> json) {
    return ApprovalItem(
      id: json['id'] as String,
      taskId: json['task_id'] as String,
      actionType: json['action_type'] as String? ?? 'general',
      description: json['description'] as String? ?? '',
      details: (json['details'] as Map<String, dynamic>?) ?? {},
      status: json['status'] as String? ?? 'pending',
      createdAt: DateTime.tryParse(json['created_at'] as String? ?? '') ?? DateTime.now(),
      resolvedAt: json['resolved_at'] != null ? DateTime.tryParse(json['resolved_at'] as String) : null,
      rejectionReason: json['rejection_reason'] as String?,
    );
  }

  bool get isPending => status == 'pending';
  bool get isApproved => status == 'approved';
  bool get isRejected => status == 'rejected';
}
