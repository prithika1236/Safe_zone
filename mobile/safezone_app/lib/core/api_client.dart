import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'config.dart';
import 'storage_service.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException({required this.statusCode, required this.message});

  @override
  String toString() => message;
}

class ApiClient {
  final StorageService _storageService;
  final http.Client _httpClient;

  ApiClient(this._storageService, [http.Client? httpClient])
      : _httpClient = httpClient ?? http.Client();

  Map<String, String> _buildHeaders() {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    final token = _storageService.getToken();
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Uri _buildUri(String path, [Map<String, dynamic>? queryParams]) {
    final base = AppConfig.apiBaseUrl;
    final cleanPath = path.startsWith('/') ? path : '/$path';
    final urlStr = '$base$cleanPath';

    if (queryParams == null || queryParams.isEmpty) {
      return Uri.parse(urlStr);
    }

    final sanitizedParams = queryParams.map(
      (k, v) => MapEntry(k, v?.toString() ?? ''),
    )..removeWhere((k, v) => v.isEmpty);

    return Uri.parse(urlStr).replace(queryParameters: sanitizedParams);
  }

  Future<dynamic> get(String path, {Map<String, dynamic>? queryParams}) async {
    try {
      final uri = _buildUri(path, queryParams);
      final response = await _httpClient
          .get(uri, headers: _buildHeaders())
          .timeout(AppConfig.requestTimeout);
      return _handleResponse(response);
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Cannot connect to SafeZone server. Please verify network connection.',
      );
    }
  }

  Future<dynamic> post(String path, {dynamic body}) async {
    try {
      final uri = _buildUri(path);
      final encodedBody = body != null ? jsonEncode(body) : null;
      final response = await _httpClient
          .post(uri, headers: _buildHeaders(), body: encodedBody)
          .timeout(AppConfig.requestTimeout);
      return _handleResponse(response);
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Cannot connect to SafeZone server. Please verify network connection.',
      );
    }
  }

  Future<dynamic> patch(String path, {dynamic body}) async {
    try {
      final uri = _buildUri(path);
      final encodedBody = body != null ? jsonEncode(body) : null;
      final response = await _httpClient
          .patch(uri, headers: _buildHeaders(), body: encodedBody)
          .timeout(AppConfig.requestTimeout);
      return _handleResponse(response);
    } on SocketException {
      throw ApiException(
        statusCode: 0,
        message: 'Cannot connect to SafeZone server. Please verify network connection.',
      );
    }
  }

  dynamic _handleResponse(http.Response response) {
    if (response.statusCode == 204) {
      return null;
    }

    dynamic decoded;
    try {
      decoded = response.body.isNotEmpty ? jsonDecode(response.body) : null;
    } catch (_) {
      decoded = null;
    }

    if (response.statusCode >= 200 && response.statusCode < 300) {
      return decoded;
    }

    String errorMsg = 'An unexpected error occurred (${response.statusCode})';
    if (decoded is Map<String, dynamic>) {
      if (decoded['detail'] != null) {
        errorMsg = decoded['detail'].toString();
      } else if (decoded['message'] != null) {
        errorMsg = decoded['message'].toString();
      }
    }

    if (response.statusCode == 401) {
      _storageService.clearSession();
    }

    throw ApiException(statusCode: response.statusCode, message: errorMsg);
  }
}
