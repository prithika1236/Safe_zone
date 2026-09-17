import 'package:flutter/foundation.dart';

/// Centralized configuration for SafeZone Mobile API communication.
class AppConfig {
  static const String _defaultAndroidUrl = 'http://10.0.2.2:8000/api/v1';
  static const String _defaultLocalhostUrl = 'http://127.0.0.1:8000/api/v1';

  /// Resolves the appropriate base URL according to the execution platform.
  static String get apiBaseUrl {
    const fromEnv = String.fromEnvironment('API_BASE_URL');
    if (fromEnv.isNotEmpty) {
      return fromEnv;
    }

    if (kIsWeb) {
      return _defaultLocalhostUrl;
    }

    if (defaultTargetPlatform == TargetPlatform.android) {
      return _defaultAndroidUrl;
    }

    return _defaultLocalhostUrl;
  }

  static const Duration requestTimeout = Duration(seconds: 15);
}
