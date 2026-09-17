import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/emergency_contact_model.dart';
import '../models/user_model.dart';

/// Secure token, emergency contacts, and session persistence using SharedPreferences.
class StorageService {
  static const String _keyToken = 'safezone_jwt_token';
  static const String _keyRole = 'safezone_user_role';
  static const String _keyUser = 'safezone_user_json';
  static const String _keyDuty = 'safezone_police_duty_status';
  static const String _keyEmergencyContacts = 'safezone_emergency_contacts_json';

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

  List<EmergencyContactModel> getEmergencyContacts() {
    final raw = _prefs.getString(_keyEmergencyContacts);
    if (raw == null) return [];
    try {
      final decoded = jsonDecode(raw) as List<dynamic>;
      return decoded
          .map((item) =>
              EmergencyContactModel.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> saveEmergencyContacts(List<EmergencyContactModel> contacts) async {
    final encoded = jsonEncode(contacts.map((c) => c.toJson()).toList());
    await _prefs.setString(_keyEmergencyContacts, encoded);
  }

  Future<void> clearSession() async {
    await _prefs.remove(_keyToken);
    await _prefs.remove(_keyRole);
    await _prefs.remove(_keyUser);
    await _prefs.remove(_keyDuty);
  }
}
