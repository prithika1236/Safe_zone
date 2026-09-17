import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_model.dart';

/// Secure token and session persistence using SharedPreferences.
class StorageService {
  static const String _keyToken = 'safezone_jwt_token';
  static const String _keyRole = 'safezone_user_role';
  static const String _keyUser = 'safezone_user_json';
  static const String _keyDuty = 'safezone_police_duty_status';

  final SharedPreferences _prefs;

  StorageService(this._prefs);

  static Future<StorageService> getInstance() async {
    final prefs = await SharedPreferences.getInstance();
    return StorageService(prefs);
  }

  Future<void> saveSession({
    required String token,
    required String role,
    required UserModel user,
  }) async {
    await _prefs.setString(_keyToken, token);
    await _prefs.setString(_keyRole, role);
    await _prefs.setString(_keyUser, jsonEncode(user.toJson()));
  }

  String? getToken() {
    return _prefs.getString(_keyToken);
  }

  String? getRole() {
    return _prefs.getString(_keyRole);
  }

  UserModel? getUser() {
    final raw = _prefs.getString(_keyUser);
    if (raw == null) return null;
    try {
      final decoded = jsonDecode(raw) as Map<String, dynamic>;
      return UserModel.fromJson(decoded);
    } catch (_) {
      return null;
    }
  }

  bool getDutyStatus() {
    return _prefs.getBool(_keyDuty) ?? true;
  }

  Future<void> setDutyStatus(bool onDuty) async {
    await _prefs.setBool(_keyDuty, onDuty);
  }

  Future<void> clearSession() async {
    await _prefs.remove(_keyToken);
    await _prefs.remove(_keyRole);
    await _prefs.remove(_keyUser);
    await _prefs.remove(_keyDuty);
  }
}
