import 'package:personal_ai_assistant_apps/models/task.dart';

class RouteResult {
  final String intent;
  final double confidence;
  final String targetService;
  final bool requiresDeepReasoning;
  final String? structuredAction;
  final Map<String, dynamic> structuredPayload;
  final double latencyMs;
  final TaskItem? createdTask;
  final String message;

  const RouteResult({
    required this.intent,
    required this.confidence,
    required this.targetService,
    this.requiresDeepReasoning = false,
    this.structuredAction,
    this.structuredPayload = const {},
    this.latencyMs = 0.0,
    this.createdTask,
    required this.message,
  });

  factory RouteResult.fromDispatchJson(Map<String, dynamic> json) {
    final decision = (json['decision'] as Map<String, dynamic>?) ?? {};
    final taskData = json['task'] as Map<String, dynamic>?;

    return RouteResult(
      intent: decision['intent'] as String? ?? 'general_query',
      confidence: (decision['confidence'] as num?)?.toDouble() ?? 0.0,
      targetService: decision['target_service'] as String? ?? 'unknown',
      requiresDeepReasoning: decision['requires_deep_reasoning'] as bool? ?? false,
      structuredAction: decision['structured_action'] as String?,
      structuredPayload: (decision['structured_payload'] as Map<String, dynamic>?) ?? {},
      latencyMs: (decision['latency_ms'] as num?)?.toDouble() ?? 0.0,
      createdTask: taskData != null ? TaskItem.fromJson(taskData) : null,
      message: json['message'] as String? ?? '',
    );
  }
}
