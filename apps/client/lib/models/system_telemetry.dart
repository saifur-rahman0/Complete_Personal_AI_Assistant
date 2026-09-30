class WindowItem {
  final String title;
  final int? handle;
  final String? processName;

  WindowItem({
    required this.title,
    this.handle,
    this.processName,
  });

  factory WindowItem.fromJson(Map<String, dynamic> json) {
    return WindowItem(
      title: json['title'] as String,
      handle: json['handle'] as int?,
      processName: json['process_name'] as String?,
    );
  }
}

class SystemTelemetryData {
  final double cpuPercent;
  final double memoryUsedPercent;
  final double memoryTotalGb;
  final int? batteryPercent;
  final bool? isCharging;
  final List<WindowItem> openWindows;
  final DateTime timestamp;

  SystemTelemetryData({
    required this.cpuPercent,
    required this.memoryUsedPercent,
    required this.memoryTotalGb,
    this.batteryPercent,
    this.isCharging,
    this.openWindows = const [],
    required this.timestamp,
  });

  factory SystemTelemetryData.fromJson(Map<String, dynamic> json) {
    var rawWindows = (json['open_windows'] as List<dynamic>?) ?? [];
    return SystemTelemetryData(
      cpuPercent: (json['cpu_percent'] as num).toDouble(),
      memoryUsedPercent: (json['memory_used_percent'] as num).toDouble(),
      memoryTotalGb: (json['memory_total_gb'] as num).toDouble(),
      batteryPercent: json['battery_percent'] as int?,
      isCharging: json['is_charging'] as bool?,
      openWindows: rawWindows
          .map((w) => WindowItem.fromJson(w as Map<String, dynamic>))
          .toList(),
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'] as String)
          : DateTime.now(),
    );
  }
}
