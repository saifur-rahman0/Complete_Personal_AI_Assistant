import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:personal_ai_assistant_apps/services/api_service.dart';

class DynamicChatBubble extends StatelessWidget {
  final Map<String, String> message;
  final Function(String path, bool reveal)? onOpenFile;

  const DynamicChatBubble({
    super.key,
    required this.message,
    this.onOpenFile,
  });

  @override
  Widget build(BuildContext context) {
    final role = message['role'] ?? 'assistant';
    final text = message['text'] ?? '';
    final isUser = role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        constraints: const BoxConstraints(maxWidth: 650),
        decoration: BoxDecoration(
          color: isUser ? Colors.cyanAccent.shade700 : const Color(0xFF1B202B),
          borderRadius: BorderRadius.circular(16).copyWith(
            bottomRight: isUser ? const Radius.circular(0) : const Radius.circular(16),
            bottomLeft: !isUser ? const Radius.circular(0) : const Radius.circular(16),
          ),
          border: isUser
              ? null
              : Border.all(color: Colors.white.withValues(alpha: 0.08)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.2),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        padding: const EdgeInsets.all(14),
        child: isUser
            ? Text(
                text,
                style: const TextStyle(
                  color: Colors.black,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  height: 1.4,
                ),
              )
            : _buildAssistantContent(context, text),
      ),
    );
  }

  Widget _buildAssistantContent(BuildContext context, String text) {
    // Check if this message represents a file/folder listing
    final fileItems = _extractFileItems(text);
    if (fileItems.isNotEmpty) {
      return _buildFileListContent(context, text, fileItems);
    }

    // Check if this message represents system telemetry
    if (text.startsWith('System Telemetry:')) {
      return _buildTelemetryContent(context, text);
    }

    // Check if message has a code/content block
    if (text.contains('```')) {
      return _buildCodeOrContent(context, text);
    }

    // Fallback: regular formatted text
    return _buildRichTextWithLinks(context, text);
  }

  // --- File List Parsing & Rendering ---

  List<_ParsedFileItem> _extractFileItems(String text) {
    final items = <_ParsedFileItem>[];
    final lines = text.split('\n');

    final linkRegex = RegExp(r'\[([^\]]+)\]\(([^)]+)\)(?:\s*[—\-•]\s*`?([^`\n]*)`?)?');

    for (final line in lines) {
      final match = linkRegex.firstMatch(line);
      if (match != null) {
        final name = match.group(1) ?? '';
        final path = match.group(2) ?? '';
        final size = match.group(3)?.trim() ?? '';
        final isDir = line.contains('📁') || size.toLowerCase().contains('folder');

        if (name.isNotEmpty && path.isNotEmpty) {
          items.add(_ParsedFileItem(
            name: name,
            path: path,
            isDir: isDir,
            sizeLabel: size.isEmpty ? (isDir ? 'Folder' : '') : size,
          ));
        }
      }
    }

    return items;
  }

  Widget _buildFileListContent(
    BuildContext context,
    String fullText,
    List<_ParsedFileItem> files,
  ) {
    // Extract header line
    final firstLine = fullText.split('\n').firstWhere(
          (l) => l.trim().isNotEmpty,
          orElse: () => 'Files:',
        );
    final cleanHeader = firstLine.replaceAll('*', '').replaceAll('`', '');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Header
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: Colors.cyanAccent.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.folder_open, color: Colors.cyanAccent, size: 18),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                cleanHeader,
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                ),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${files.length} items',
                style: const TextStyle(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Interactive File List
        ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 340),
          child: ListView.separated(
            shrinkWrap: true,
            itemCount: files.length,
            separatorBuilder: (_, __) => const SizedBox(height: 6),
            itemBuilder: (context, index) {
              final file = files[index];
              return _buildFileItemTile(context, file);
            },
          ),
        ),

        const SizedBox(height: 8),
        // Tip footer
        Row(
          children: [
            Icon(Icons.touch_app, size: 13, color: Colors.grey.shade500),
            const SizedBox(width: 4),
            Text(
              'Click item or Open button to launch on your workstation.',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 11, fontStyle: FontStyle.italic),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildFileItemTile(BuildContext context, _ParsedFileItem file) {
    final iconData = _getIconForFile(file.name, file.isDir);
    final iconColor = _getColorForFile(file.name, file.isDir);

    return InkWell(
      onTap: () => _openFile(context, file.path, reveal: false),
      borderRadius: BorderRadius.circular(8),
      hoverColor: Colors.white.withValues(alpha: 0.04),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xFF131720),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
        ),
        child: Row(
          children: [
            Icon(iconData, color: iconColor, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    file.name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (file.path != file.name)
                    Text(
                      file.path,
                      style: TextStyle(
                        color: Colors.grey.shade500,
                        fontSize: 11,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
            if (file.sizeLabel.isNotEmpty) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  file.sizeLabel,
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 10),
                ),
              ),
            ],
            const SizedBox(width: 6),
            // Open Button
            IconButton(
              icon: const Icon(Icons.open_in_new, size: 16, color: Colors.cyanAccent),
              tooltip: 'Open',
              constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
              padding: EdgeInsets.zero,
              onPressed: () => _openFile(context, file.path, reveal: false),
            ),
            // Reveal in Folder Button
            IconButton(
              icon: Icon(Icons.folder_shared_outlined, size: 16, color: Colors.grey.shade400),
              tooltip: 'Show in Explorer',
              constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
              padding: EdgeInsets.zero,
              onPressed: () => _openFile(context, file.path, reveal: true),
            ),
          ],
        ),
      ),
    );
  }

  // --- Telemetry Dashboard Widget ---

  Widget _buildTelemetryContent(BuildContext context, String text) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            const Icon(Icons.speed, color: Colors.tealAccent, size: 20),
            const SizedBox(width: 8),
            const Text(
              'System Workstation Telemetry',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: const Color(0xFF131720),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.tealAccent.withValues(alpha: 0.3)),
          ),
          child: Text(
            text,
            style: const TextStyle(color: Colors.tealAccent, fontSize: 13, height: 1.4),
          ),
        ),
      ],
    );
  }

  // --- Code or Content Block ---

  Widget _buildCodeOrContent(BuildContext context, String text) {
    final parts = text.split('```');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < parts.length; i++)
          if (i % 2 == 1)
            Container(
              margin: const EdgeInsets.symmetric(vertical: 6),
              decoration: BoxDecoration(
                color: const Color(0xFF0F121A),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(8)),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'CONTENT',
                          style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy, size: 14, color: Colors.cyanAccent),
                          tooltip: 'Copy',
                          constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                          padding: EdgeInsets.zero,
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: parts[i]));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Copied to clipboard'), duration: Duration(seconds: 1)),
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: SelectableText(
                      parts[i].trim(),
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        color: Colors.tealAccent,
                        fontSize: 12,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            )
          else if (parts[i].trim().isNotEmpty)
            _buildRichTextWithLinks(context, parts[i].trim()),
      ],
    );
  }

  // --- Plain Rich Text with Fallback Link Clicks ---

  Widget _buildRichTextWithLinks(BuildContext context, String text) {
    return SelectableText(
      text,
      style: const TextStyle(
        color: Colors.white,
        fontSize: 14,
        height: 1.45,
      ),
    );
  }

  // --- Helper Methods ---

  void _openFile(BuildContext context, String path, {bool reveal = true}) {
    if (onOpenFile != null) {
      onOpenFile!(path, reveal);
      return;
    }

    final name = path.split(RegExp(r'[\\/]')).last;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(reveal ? 'Revealing $name in Explorer...' : 'Opening $name...'),
        duration: const Duration(seconds: 2),
        backgroundColor: const Color(0xFF1B202B),
      ),
    );

    apiService.openPath(path, reveal: reveal);
  }

  IconData _getIconForFile(String name, bool isDir) {
    if (isDir) return Icons.folder;
    final lower = name.toLowerCase();
    if (lower.endsWith('.pdf')) return Icons.picture_as_pdf;
    if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.gif')) {
      return Icons.image;
    }
    if (lower.endsWith('.mp4') || lower.endsWith('.mkv') || lower.endsWith('.mov') || lower.endsWith('.avi')) {
      return Icons.movie;
    }
    if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.flac')) {
      return Icons.audiotrack;
    }
    if (lower.endsWith('.zip') || lower.endsWith('.rar') || lower.endsWith('.7z') || lower.endsWith('.tar')) {
      return Icons.archive;
    }
    if (lower.endsWith('.exe') || lower.endsWith('.msi')) return Icons.system_update_alt;
    if (lower.endsWith('.py') || lower.endsWith('.dart') || lower.endsWith('.json') || lower.endsWith('.js')) {
      return Icons.code;
    }
    return Icons.insert_drive_file;
  }

  Color _getColorForFile(String name, bool isDir) {
    if (isDir) return Colors.amber;
    final lower = name.toLowerCase();
    if (lower.endsWith('.pdf')) return Colors.redAccent;
    if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return Colors.purpleAccent;
    if (lower.endsWith('.zip') || lower.endsWith('.rar') || lower.endsWith('.7z')) return Colors.orangeAccent;
    if (lower.endsWith('.exe') || lower.endsWith('.msi')) return Colors.cyanAccent;
    if (lower.endsWith('.py') || lower.endsWith('.dart') || lower.endsWith('.json')) return Colors.tealAccent;
    return Colors.lightBlueAccent;
  }
}

class _ParsedFileItem {
  final String name;
  final String path;
  final bool isDir;
  final String sizeLabel;

  _ParsedFileItem({
    required this.name,
    required this.path,
    required this.isDir,
    required this.sizeLabel,
  });
}
