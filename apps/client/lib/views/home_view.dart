import 'dart:async';
import 'package:flutter/material.dart';
import 'package:personal_ai_assistant_apps/models/approval.dart';
import 'package:personal_ai_assistant_apps/models/task.dart';
import 'package:personal_ai_assistant_apps/services/api_service.dart';
import 'package:personal_ai_assistant_apps/widgets/approval_card.dart';
import 'package:personal_ai_assistant_apps/widgets/command_input.dart';
import 'package:personal_ai_assistant_apps/widgets/device_sync_dialog.dart';
import 'package:personal_ai_assistant_apps/widgets/task_card.dart';

class HomeView extends StatefulWidget {
  const HomeView({super.key});

  @override
  State<HomeView> createState() => _HomeViewState();
}

class _HomeViewState extends State<HomeView> {
  List<TaskItem> _tasks = [];
  List<ApprovalItem> _pendingApprovals = [];
  final List<Map<String, String>> _messages = [
    {
      'role': 'assistant',
      'text': 'Hello! I am your AI assistant. You can give me file management commands, search instructions, or ask questions.',
    }
  ];

  bool _isLoading = false;
  bool _isResolvingApproval = false;
  bool _isBackendOnline = false;
  bool _isRefreshing = false;
  Timer? _pollingTimer;

  int _selectedMobileTab = 0;

  @override
  void initState() {
    super.initState();
    _refreshData();
    // Poll every 4 seconds with concurrency guard to avoid network congestion
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (_) => _refreshData(silent: true));
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  void _showSyncDialog() {
    showDialog(
      context: context,
      builder: (context) => DeviceSyncDialog(
        onSyncCompleted: () => _refreshData(),
      ),
    );
  }

  Future<void> _refreshData({bool silent = false}) async {
    if (_isRefreshing) return; // Prevent overlapping HTTP calls on mobile
    _isRefreshing = true;

    try {
      final online = await apiService.checkHealth();
      if (!mounted) return;

      if (online) {
        final tasks = await apiService.getTasks();
        final approvals = await apiService.getPendingApprovals();
        final sharedChats = await apiService.getChatHistory();

        if (!mounted) return;
        setState(() {
          _isBackendOnline = true;
          _tasks = tasks;
          _pendingApprovals = approvals;
          if (sharedChats.isNotEmpty) {
            _messages.clear();
            _messages.addAll(sharedChats);
          }
        });
      } else {
        if (!mounted) return;
        setState(() {
          _isBackendOnline = false;
        });
      }
    } catch (_) {
      // Gracefully handle network blips
    } finally {
      _isRefreshing = false;
    }
  }

  Future<void> _handleCommand(String prompt) async {
    setState(() {
      _isLoading = true;
      _messages.add({'role': 'user', 'text': prompt});
    });

    try {
      final result = await apiService.dispatchPrompt(prompt);
      if (!mounted) return;

      setState(() {
        _messages.add({
          'role': 'assistant',
          'text': result.message,
        });
      });
      await _refreshData();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add({
          'role': 'assistant',
          'text': 'Error connecting to backend: $e',
        });
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _handleResolveApproval(ApprovalItem approval, bool approved) async {
    setState(() => _isResolvingApproval = true);
    await apiService.resolveApproval(approval.id, approved);

    if (!mounted) return;
    setState(() => _isResolvingApproval = false);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(approved ? 'Action approved. Resuming execution...' : 'Action rejected.'),
        backgroundColor: approved ? Colors.teal : Colors.redAccent,
        duration: const Duration(seconds: 2),
      ),
    );

    await _refreshData();
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isDesktop = constraints.maxWidth > 750;
        return Scaffold(
          backgroundColor: const Color(0xFF0F121A),
          appBar: AppBar(
            backgroundColor: const Color(0xFF161B26),
            elevation: 0,
            title: Row(
              children: [
                const Icon(Icons.bolt, color: Colors.cyanAccent),
                const SizedBox(width: 8),
                const Text(
                  'Jarvis Assistant',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.sync, color: Colors.cyanAccent, size: 20),
                  tooltip: 'Connect & Pair Device',
                  onPressed: _showSyncDialog,
                ),
                const SizedBox(width: 4),
                InkWell(
                  onTap: _showSyncDialog,
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: _isBackendOnline ? Colors.teal.withValues(alpha: 0.2) : Colors.red.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _isBackendOnline ? Colors.tealAccent : Colors.redAccent,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _isBackendOnline
                              ? (apiService.isPaired ? 'SYNCED' : 'ONLINE')
                              : 'CONNECT',
                          style: TextStyle(
                            color: _isBackendOnline ? Colors.tealAccent : Colors.redAccent,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          body: isDesktop ? _buildDesktopLayout() : _buildMobileLayout(),
          bottomNavigationBar: isDesktop ? null : _buildMobileBottomNav(),
        );
      },
    );
  }

  // Desktop Split Layout (Wide Screen)
  Widget _buildDesktopLayout() {
    return Row(
      children: [
        // Left Column: Command & Chat stream
        Expanded(
          flex: 6,
          child: Column(
            children: [
              Expanded(child: _buildChatList()),
              CommandInput(onSubmitted: _handleCommand, isLoading: _isLoading),
            ],
          ),
        ),
        // Vertical Divider
        Container(width: 1, color: Colors.white.withValues(alpha: 0.08)),
        // Right Column: Approvals & Task timeline
        Expanded(
          flex: 4,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (_pendingApprovals.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                  child: Text(
                    'PENDING APPROVALS (${_pendingApprovals.length})',
                    style: const TextStyle(
                      color: Colors.amber,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 1.1,
                    ),
                  ),
                ),
                ..._pendingApprovals.map((appr) => ApprovalCard(
                      approval: appr,
                      isResolving: _isResolvingApproval,
                      onResolve: (approved) => _handleResolveApproval(appr, approved),
                    )),
                const Divider(color: Colors.white12),
              ],
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Text(
                  'ACTIVE TASKS (${_tasks.length})',
                  style: TextStyle(
                    color: Colors.grey.shade400,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
              Expanded(
                child: _tasks.isEmpty
                    ? Center(
                        child: Text(
                          'No tasks enqueued yet.',
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _tasks.length,
                        itemBuilder: (context, index) => TaskCard(task: _tasks[index]),
                      ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // Mobile Companion Layout (Phone Screen)
  Widget _buildMobileLayout() {
    if (_selectedMobileTab == 0) {
      // Assistant / Command view
      return Column(
        children: [
          if (_pendingApprovals.isNotEmpty)
            InkWell(
              onTap: () => setState(() => _selectedMobileTab = 2),
              child: Container(
                margin: const EdgeInsets.all(8),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.amber.withValues(alpha: 0.5)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.shield_outlined, color: Colors.amber, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${_pendingApprovals.length} action(s) require your approval!',
                        style: const TextStyle(color: Colors.amber, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                    ),
                    const Icon(Icons.arrow_forward_ios, color: Colors.amber, size: 14),
                  ],
                ),
              ),
            ),
          Expanded(child: _buildChatList()),
          CommandInput(onSubmitted: _handleCommand, isLoading: _isLoading),
        ],
      );
    } else if (_selectedMobileTab == 1) {
      // Tasks list
      return _tasks.isEmpty
          ? Center(child: Text('No active tasks.', style: TextStyle(color: Colors.grey.shade500)))
          : ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: _tasks.length,
              itemBuilder: (context, index) => TaskCard(task: _tasks[index]),
            );
    } else {
      // Approvals view (Android Companion Core Focus)
      return _pendingApprovals.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.check_circle_outline, color: Colors.tealAccent, size: 48),
                  const SizedBox(height: 12),
                  const Text('No pending approvals', style: TextStyle(color: Colors.white, fontSize: 16)),
                  const SizedBox(height: 4),
                  Text('All agent actions are up to date.', style: TextStyle(color: Colors.grey.shade500)),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: _pendingApprovals.length,
              itemBuilder: (context, index) => ApprovalCard(
                approval: _pendingApprovals[index],
                isResolving: _isResolvingApproval,
                onResolve: (approved) => _handleResolveApproval(_pendingApprovals[index], approved),
              ),
            );
    }
  }

  Widget _buildChatList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _messages.length,
      itemBuilder: (context, index) {
        final msg = _messages[index];
        final isUser = msg['role'] == 'user';

        return Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 6),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            constraints: const BoxConstraints(maxWidth: 550),
            decoration: BoxDecoration(
              color: isUser ? Colors.cyanAccent.shade700 : const Color(0xFF1B202B),
              borderRadius: BorderRadius.circular(16).copyWith(
                bottomRight: isUser ? const Radius.circular(0) : const Radius.circular(16),
                bottomLeft: !isUser ? const Radius.circular(0) : const Radius.circular(16),
              ),
            ),
            child: Text(
              msg['text']!,
              style: TextStyle(
                color: isUser ? Colors.black : Colors.white,
                fontSize: 14,
                height: 1.4,
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildMobileBottomNav() {
    return NavigationBar(
      backgroundColor: const Color(0xFF161B26),
      selectedIndex: _selectedMobileTab,
      onDestinationSelected: (index) => setState(() => _selectedMobileTab = index),
      destinations: [
        const NavigationDestination(
          icon: Icon(Icons.chat_bubble_outline),
          selectedIcon: Icon(Icons.chat_bubble, color: Colors.cyanAccent),
          label: 'Assistant',
        ),
        const NavigationDestination(
          icon: Icon(Icons.checklist),
          selectedIcon: Icon(Icons.checklist, color: Colors.cyanAccent),
          label: 'Tasks',
        ),
        NavigationDestination(
          icon: Badge(
            isLabelVisible: _pendingApprovals.isNotEmpty,
            label: Text('${_pendingApprovals.length}'),
            backgroundColor: Colors.amber,
            child: const Icon(Icons.shield_outlined),
          ),
          selectedIcon: const Icon(Icons.shield, color: Colors.amber),
          label: 'Approvals',
        ),
      ],
    );
  }
}
