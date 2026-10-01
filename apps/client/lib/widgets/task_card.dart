import 'package:flutter/material.dart';
import 'package:personal_ai_assistant_apps/models/task.dart';
import 'package:personal_ai_assistant_apps/services/api_service.dart';

class TaskCard extends StatelessWidget {
  final TaskItem task;

  const TaskCard({super.key, required this.task});

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor(task.status);

    return Card(
      elevation: 2,
      margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      color: const Color(0xFF1B202B),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  task.targetDevice == 'windows' ? Icons.laptop_windows : Icons.phone_android,
                  size: 18,
                  color: Colors.grey.shade400,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    task.title,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: statusColor.withValues(alpha: 0.5)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (task.isRunning) ...[
                        SizedBox(
                          width: 10,
                          height: 10,
                          child: CircularProgressIndicator(strokeWidth: 1.5, color: statusColor),
                        ),
                        const SizedBox(width: 5),
                      ],
                      Text(
                        task.status.toUpperCase().replaceAll('_', ' '),
                        style: TextStyle(
                          color: statusColor,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (task.description != null && task.description!.isNotEmpty && task.description != task.title) ...[
              const SizedBox(height: 6),
              Text(
                task.description!,
                style: TextStyle(color: Colors.grey.shade400, fontSize: 13),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],
            if (task.resultSummary != null) ...[
              const SizedBox(height: 8),
              _buildTaskResult(context, task.resultSummary!),
            ],
            if (task.errorMessage != null) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.red.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  task.errorMessage!,
                  style: const TextStyle(color: Colors.redAccent, fontSize: 12),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Color _statusColor(String status) {
    switch (status.toLowerCase()) {
      case 'running':
        return Colors.lightBlueAccent;
      case 'completed':
        return Colors.tealAccent;
      case 'awaiting_approval':
        return Colors.amber;
      case 'failed':
      case 'cancelled':
        return Colors.redAccent;
      case 'pending':
      default:
        return Colors.grey.shade400;
    }
  }

  Widget _buildTaskResult(BuildContext context, String summary) {
    final linkRegex = RegExp(r'\[([^\]]+)\]\(([^)]+)\)');
    final matches = linkRegex.allMatches(summary).toList();

    if (matches.isNotEmpty) {
      final firstLine = summary.split('\n').first.replaceAll('*', '').replaceAll('`', '');
      return Container(
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Colors.teal.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.tealAccent.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(firstLine, style: const TextStyle(color: Colors.tealAccent, fontSize: 12, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 180),
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: matches.length,
                separatorBuilder: (_, __) => const SizedBox(height: 4),
                itemBuilder: (context, i) {
                  final m = matches[i];
                  final name = m.group(1) ?? '';
                  final path = m.group(2) ?? '';
                  return InkWell(
                    onTap: () => apiService.openPath(path, reveal: false),
                    borderRadius: BorderRadius.circular(4),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 4),
                      child: Row(
                        children: [
                          const Icon(Icons.description, size: 14, color: Colors.tealAccent),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              name,
                              style: const TextStyle(color: Colors.white, fontSize: 11),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.open_in_new, size: 13, color: Colors.tealAccent),
                            tooltip: 'Open',
                            constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                            padding: EdgeInsets.zero,
                            onPressed: () => apiService.openPath(path, reveal: false),
                          ),
                          IconButton(
                            icon: Icon(Icons.folder_shared_outlined, size: 13, color: Colors.grey.shade400),
                            tooltip: 'Show in Explorer',
                            constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                            padding: EdgeInsets.zero,
                            onPressed: () => apiService.openPath(path, reveal: true),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.teal.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        summary,
        style: const TextStyle(color: Colors.tealAccent, fontSize: 12),
      ),
    );
  }
}
