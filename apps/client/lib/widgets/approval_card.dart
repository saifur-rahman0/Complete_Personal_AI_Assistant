import 'package:flutter/material.dart';
import 'package:personal_ai_assistant_apps/models/approval.dart';

class ApprovalCard extends StatelessWidget {
  final ApprovalItem approval;
  final Function(bool approved) onResolve;
  final bool isResolving;

  const ApprovalCard({
    super.key,
    required this.approval,
    required this.onResolve,
    this.isResolving = false,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 4,
      margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: Colors.amber, width: 1.5),
      ),
      color: const Color(0xFF1E222D),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.shield_outlined, color: Colors.amber, size: 16),
                      const SizedBox(width: 6),
                      Text(
                        approval.actionType.toUpperCase(),
                        style: const TextStyle(
                          color: Colors.amber,
                          fontWeight: FontWeight.bold,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                const Text(
                  'ACTION REQUIRED',
                  style: TextStyle(
                    color: Colors.amberAccent,
                    fontSize: 11,
                    letterSpacing: 1.1,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              approval.description,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
            if (approval.details.isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.black26,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _formatDetails(approval.details),
                  style: TextStyle(
                    color: Colors.grey.shade300,
                    fontSize: 13,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),
            if (isResolving)
              const Center(
                child: SizedBox(
                  height: 24,
                  width: 24,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.amber),
                ),
              )
            else
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.redAccent,
                        side: const BorderSide(color: Colors.redAccent),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: () => onResolve(false),
                      icon: const Icon(Icons.close, size: 18),
                      label: const Text('Reject', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.tealAccent.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: () => onResolve(true),
                      icon: const Icon(Icons.check, size: 18),
                      label: const Text('Approve', style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  String _formatDetails(Map<String, dynamic> details) {
    if (details.containsKey('total_files')) {
      final total = details['total_files'];
      final categories = details['categories'] as Map<String, dynamic>? ?? {};
      return 'Plan: Move $total files into [${categories.keys.join(", ")}]';
    }
    if (details.containsKey('destination')) {
      return 'Destination: ${details["destination"]}';
    }
    return details.entries.map((e) => '${e.key}: ${e.value}').take(3).join('\n');
  }
}
