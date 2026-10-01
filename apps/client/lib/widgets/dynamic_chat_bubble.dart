import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:personal_ai_assistant_apps/services/api_service.dart';

class DynamicChatBubble extends StatefulWidget {
  final Map<String, String> message;
  final Function(String path, bool reveal)? onOpenFile;

  const DynamicChatBubble({
    super.key,
    required this.message,
    this.onOpenFile,
  });

  @override
  State<DynamicChatBubble> createState() => _DynamicChatBubbleState();
}

class _DynamicChatBubbleState extends State<DynamicChatBubble> {
  final TextEditingController _filterController = TextEditingController();
  String _filterQuery = '';

  @override
  void dispose() {
    _filterController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final role = widget.message['role'] ?? 'assistant';
    final text = widget.message['text'] ?? '';
    final isUser = role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        constraints: const BoxConstraints(maxWidth: 680),
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
    // 1. Check if this message represents a file/folder listing
    final fileItems = _extractFileItems(text);
    if (fileItems.isNotEmpty) {
      return _buildFileListContent(context, text, fileItems);
    }

    // 2. Check if this message represents system telemetry
    if (text.startsWith('System Telemetry:')) {
      return _buildTelemetryContent(context, text);
    }

    // 3. Check if message has a code/content block
    if (text.contains('```')) {
      return _buildCodeOrContent(context, text);
    }

    // 4. Fallback: regular formatted text
    return _buildRichTextWithLinks(context, text);
  }

  // --- File List Parsing & Interactive Rendering ---

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

    // Filter files based on user real-time search
    final displayedFiles = _filterQuery.isEmpty
        ? files
        : files.where((f) {
            return f.name.toLowerCase().contains(_filterQuery) ||
                f.path.toLowerCase().contains(_filterQuery);
          }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Header Row
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
                _filterQuery.isEmpty
                    ? '${files.length} items'
                    : '${displayedFiles.length} of ${files.length}',
                style: const TextStyle(color: Colors.cyanAccent, fontSize: 11, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // Real-time Search / Filter bar inside the card
        if (files.length > 2) ...[
          Container(
            height: 36,
            decoration: BoxDecoration(
              color: const Color(0xFF131720),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
            ),
            child: TextField(
              controller: _filterController,
              onChanged: (val) {
                setState(() {
                  _filterQuery = val.trim().toLowerCase();
                });
              },
              style: const TextStyle(color: Colors.white, fontSize: 12),
              decoration: InputDecoration(
                hintText: 'Filter specific files (e.g. resume, pdf, sheet)...',
                hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                prefixIcon: const Icon(Icons.search, size: 16, color: Colors.cyanAccent),
                suffixIcon: _filterQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 14, color: Colors.grey),
                        padding: EdgeInsets.zero,
                        onPressed: () {
                          _filterController.clear();
                          setState(() {
                            _filterQuery = '';
                          });
                        },
                      )
                    : null,
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],

        // Interactive File List
        if (displayedFiles.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Center(
              child: Text(
                'No files matching "$_filterQuery"',
                style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
              ),
            ),
          )
        else
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 340),
            child: ListView.separated(
              shrinkWrap: true,
              itemCount: displayedFiles.length,
              separatorBuilder: (context, index) => const SizedBox(height: 6),
              itemBuilder: (context, index) {
                final file = displayedFiles[index];
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
              tooltip: 'Open file',
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
            // Quick Actions Menu
            PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert, size: 16, color: Colors.grey),
              tooltip: 'Quick Actions',
              color: const Color(0xFF1B202B),
              elevation: 8,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
              ),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 30, minHeight: 30),
              onSelected: (action) => _handleQuickAction(context, file, action),
              itemBuilder: (ctx) => [
                const PopupMenuItem(
                  value: 'preview',
                  height: 36,
                  child: Row(
                    children: [
                      Icon(Icons.visibility, size: 16, color: Colors.cyanAccent),
                      SizedBox(width: 8),
                      Text('Preview Content', style: TextStyle(color: Colors.white, fontSize: 13)),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'copy_path',
                  height: 36,
                  child: Row(
                    children: [
                      Icon(Icons.copy, size: 16, color: Colors.tealAccent),
                      SizedBox(width: 8),
                      Text('Copy Path', style: TextStyle(color: Colors.white, fontSize: 13)),
                    ],
                  ),
                ),
                const PopupMenuDivider(height: 8),
                const PopupMenuItem(
                  value: 'rename',
                  height: 36,
                  child: Row(
                    children: [
                      Icon(Icons.edit_outlined, size: 16, color: Colors.amberAccent),
                      SizedBox(width: 8),
                      Text('Rename', style: TextStyle(color: Colors.white, fontSize: 13)),
                    ],
                  ),
                ),
                const PopupMenuItem(
                  value: 'move',
                  height: 36,
                  child: Row(
                    children: [
                      Icon(Icons.drive_file_move_outlined, size: 16, color: Colors.lightBlueAccent),
                      SizedBox(width: 8),
                      Text('Move To...', style: TextStyle(color: Colors.white, fontSize: 13)),
                    ],
                  ),
                ),
                const PopupMenuDivider(height: 8),
                const PopupMenuItem(
                  value: 'delete',
                  height: 36,
                  child: Row(
                    children: [
                      Icon(Icons.delete_outline, size: 16, color: Colors.redAccent),
                      SizedBox(width: 8),
                      Text('Delete / Recycle', style: TextStyle(color: Colors.redAccent, fontSize: 13)),
                    ],
                  ),
                ),
              ],
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
    if (widget.onOpenFile != null) {
      widget.onOpenFile!(path, reveal);
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

  void _handleQuickAction(BuildContext context, _ParsedFileItem file, String action) {
    switch (action) {
      case 'preview':
        _showFilePreviewModal(context, file);
        break;
      case 'copy_path':
        Clipboard.setData(ClipboardData(text: file.path));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Copied path: ${file.path}'),
            duration: const Duration(seconds: 2),
            backgroundColor: const Color(0xFF1B202B),
          ),
        );
        break;
      case 'rename':
        _showRenameDialog(context, file);
        break;
      case 'move':
        _showMoveDialog(context, file);
        break;
      case 'delete':
        _showDeleteConfirmDialog(context, file);
        break;
    }
  }

  void _showFilePreviewModal(BuildContext context, _ParsedFileItem file) {
    showDialog(
      context: context,
      builder: (dialogCtx) {
        return Dialog(
          backgroundColor: const Color(0xFF131720),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
          ),
          child: Container(
            width: 700,
            height: 520,
            padding: const EdgeInsets.all(16),
            child: FutureBuilder<Map<String, dynamic>?>(
              future: apiService.readFile(file.path),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircularProgressIndicator(color: Colors.cyanAccent),
                        SizedBox(height: 12),
                        Text('Reading file content...', style: TextStyle(color: Colors.grey)),
                      ],
                    ),
                  );
                }

                if (snapshot.hasError || snapshot.data == null) {
                  return Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.error_outline, color: Colors.redAccent, size: 36),
                        const SizedBox(height: 10),
                        Text(
                          'Could not preview "${file.name}".',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'File might be binary (e.g. PDF/EXE) or access was denied.',
                          style: TextStyle(color: Colors.grey, fontSize: 12),
                        ),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () {
                            Navigator.pop(dialogCtx);
                            apiService.openPath(file.path, reveal: false);
                          },
                          icon: const Icon(Icons.open_in_new, size: 14),
                          label: const Text('Open in Default App'),
                        ),
                      ],
                    ),
                  );
                }

                final data = snapshot.data!;
                final content = data['content'] as String? ?? '';
                final isTruncated = data['truncated'] == true;

                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header
                    Row(
                      children: [
                        const Icon(Icons.article_outlined, color: Colors.cyanAccent, size: 20),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                file.name,
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              Text(
                                file.path,
                                style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy, size: 16, color: Colors.cyanAccent),
                          tooltip: 'Copy Content',
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: content));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Content copied to clipboard'), duration: Duration(seconds: 1)),
                            );
                          },
                        ),
                        IconButton(
                          icon: const Icon(Icons.close, size: 18, color: Colors.grey),
                          onPressed: () => Navigator.pop(dialogCtx),
                        ),
                      ],
                    ),
                    const Divider(color: Colors.white12, height: 16),
                    // Content
                    Expanded(
                      child: Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F121A),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
                        ),
                        child: content.isEmpty
                            ? const Center(child: Text('(File is empty)', style: TextStyle(color: Colors.grey)))
                            : SingleChildScrollView(
                                child: SelectableText(
                                  content,
                                  style: const TextStyle(
                                    fontFamily: 'monospace',
                                    color: Colors.tealAccent,
                                    fontSize: 12,
                                    height: 1.45,
                                  ),
                                ),
                              ),
                      ),
                    ),
                    if (isTruncated) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Preview truncated for performance. Total size: ${file.sizeLabel}',
                        style: TextStyle(color: Colors.amber.shade400, fontSize: 11, fontStyle: FontStyle.italic),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
        );
      },
    );
  }

  void _showRenameDialog(BuildContext context, _ParsedFileItem file) {
    final controller = TextEditingController(text: file.name);
    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B202B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
          ),
          title: const Text('Rename File', style: TextStyle(color: Colors.white, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Original: ${file.name}',
                style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                autofocus: true,
                style: const TextStyle(color: Colors.white, fontSize: 13),
                decoration: InputDecoration(
                  labelText: 'New file name',
                  labelStyle: const TextStyle(color: Colors.cyanAccent),
                  filled: true,
                  fillColor: const Color(0xFF131720),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.cyanAccent.shade700),
              onPressed: () async {
                final newName = controller.text.trim();
                if (newName.isEmpty || newName == file.name) {
                  Navigator.pop(dialogCtx);
                  return;
                }
                Navigator.pop(dialogCtx);
                final res = await apiService.renameFile(file.path, newName);
                if (!context.mounted) return;
                if (res != null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Renamed to "$newName" successfully!'),
                      backgroundColor: Colors.teal.shade800,
                    ),
                  );
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Failed to rename file. Check filename or permissions.'),
                      backgroundColor: Colors.redAccent,
                    ),
                  );
                }
              },
              child: const Text('Rename', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            ),
          ],
        );
      },
    );
  }

  void _showMoveDialog(BuildContext context, _ParsedFileItem file) {
    showDialog(
      context: context,
      builder: (dialogCtx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1B202B),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
          ),
          title: Text('Move "${file.name}"', style: const TextStyle(color: Colors.white, fontSize: 16)),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Select destination folder:', style: TextStyle(color: Colors.grey, fontSize: 12)),
              const SizedBox(height: 12),
              _buildMoveFolderOption(dialogCtx, context, file, 'Documents', 'Documents'),
              const SizedBox(height: 6),
              _buildMoveFolderOption(dialogCtx, context, file, 'Downloads', 'Downloads'),
              const SizedBox(height: 6),
              _buildMoveFolderOption(dialogCtx, context, file, 'Desktop', 'Desktop'),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogCtx),
              child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
            ),
          ],
        );
      },
    );
  }

  Widget _buildMoveFolderOption(
    BuildContext dialogCtx,
    BuildContext scaffoldCtx,
    _ParsedFileItem file,
    String label,
    String folderName,
  ) {
    return InkWell(
      onTap: () async {
        Navigator.pop(dialogCtx);
        final userProfile = Platform.environment['USERPROFILE'] ?? '';
        final destDir = userProfile.isNotEmpty ? '$userProfile\\$folderName' : folderName;
        final res = await apiService.moveFile(file.path, destDir);
        if (!scaffoldCtx.mounted) return;
        if (res != null) {
          ScaffoldMessenger.of(scaffoldCtx).showSnackBar(
            SnackBar(
              content: Text('Moved "${file.name}" to $folderName!'),
              backgroundColor: Colors.teal.shade800,
            ),
          );
        } else {
          ScaffoldMessenger.of(scaffoldCtx).showSnackBar(
            SnackBar(
              content: Text('Failed to move "${file.name}".'),
              backgroundColor: Colors.redAccent,
            ),
          );
        }
      },
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFF131720),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            const Icon(Icons.folder, color: Colors.amber, size: 18),
            const SizedBox(width: 10),
            Text(label, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500)),
            const Spacer(),
            const Icon(Icons.arrow_forward_ios, color: Colors.grey, size: 12),
          ],
        ),
      ),
    );
  }

  void _showDeleteConfirmDialog(BuildContext context, _ParsedFileItem file) {
    bool permanent = false;
    showDialog(
      context: context,
      builder: (dialogCtx) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF1B202B),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: Colors.redAccent.withValues(alpha: 0.3)),
              ),
              title: const Row(
                children: [
                  Icon(Icons.warning_amber_rounded, color: Colors.redAccent, size: 22),
                  SizedBox(width: 8),
                  Text('Confirm Delete', style: TextStyle(color: Colors.white, fontSize: 16)),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Are you sure you want to delete "${file.name}"?',
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    file.path,
                    style: TextStyle(color: Colors.grey.shade400, fontSize: 11),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Checkbox(
                        value: permanent,
                        activeColor: Colors.redAccent,
                        onChanged: (val) {
                          setDialogState(() {
                            permanent = val ?? false;
                          });
                        },
                      ),
                      const Text(
                        'Permanent delete (skip Recycle Bin)',
                        style: TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    ],
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(dialogCtx),
                  child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent.shade700),
                  onPressed: () async {
                    Navigator.pop(dialogCtx);
                    final ok = await apiService.deleteFile(file.path, permanent: permanent);
                    if (!context.mounted) return;
                    if (ok) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(permanent ? 'Permanently deleted "${file.name}"' : 'Moved "${file.name}" to Recycle Bin'),
                          backgroundColor: Colors.teal.shade800,
                        ),
                      );
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Failed to delete "${file.name}".'),
                          backgroundColor: Colors.redAccent,
                        ),
                      );
                    }
                  },
                  child: const Text('Delete', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                ),
              ],
            );
          },
        );
      },
    );
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
