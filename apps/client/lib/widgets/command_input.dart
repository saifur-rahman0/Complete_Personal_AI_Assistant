import 'package:flutter/material.dart';

class CommandInput extends StatefulWidget {
  final Function(String command) onSubmitted;
  final bool isLoading;

  const CommandInput({
    super.key,
    required this.onSubmitted,
    this.isLoading = false,
  });

  @override
  State<CommandInput> createState() => _CommandInputState();
}

class _CommandInputState extends State<CommandInput> {
  final TextEditingController _controller = TextEditingController();

  final List<String> suggestions = [
    'Organize my Downloads folder',
    'Find all PDF files in Documents',
    'Preview organizing Downloads',
    'Remind me to backup files at 6 PM',
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final text = _controller.text.trim();
    if (text.isNotEmpty && !widget.isLoading) {
      widget.onSubmitted(text);
      _controller.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Quick suggestion chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: Row(
            children: suggestions.map((s) {
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ActionChip(
                  label: Text(s, style: const TextStyle(fontSize: 12, color: Colors.white70)),
                  backgroundColor: const Color(0xFF1E2433),
                  side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  onPressed: () {
                    _controller.text = s;
                    _submit();
                  },
                ),
              );
            }).toList(),
          ),
        ),
        // Input text field
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFF161B26),
            border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.08))),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  enabled: !widget.isLoading,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    hintText: 'Ask Jarvis or give a file command...',
                    hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 14),
                    filled: true,
                    fillColor: const Color(0xFF1E2433),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  onSubmitted: (_) => _submit(),
                ),
              ),
              const SizedBox(width: 8),
              widget.isLoading
                  ? const SizedBox(
                      width: 44,
                      height: 44,
                      child: Center(
                        child: SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.cyanAccent),
                        ),
                      ),
                    )
                  : IconButton.filled(
                      style: IconButton.styleFrom(
                        backgroundColor: Colors.cyanAccent.shade700,
                        foregroundColor: Colors.black,
                      ),
                      onPressed: _submit,
                      icon: const Icon(Icons.arrow_upward_rounded),
                    ),
            ],
          ),
        ),
      ],
    );
  }
}
