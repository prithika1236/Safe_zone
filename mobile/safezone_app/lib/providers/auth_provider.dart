import 'package:flutter/foundation.dart';
import '../core/api_client.dart';
import '../core/storage_service.dart';
import '../models/user_model.dart';

class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final StorageService _storageService;

  UserModel? _currentUser;
  String? _token;
  bool _isLoading = false;
  bool _isInitialized = false;
  String? _errorMessage;

  AuthProvider(this._apiClient, this._storageService) {
    checkSession();
  }

  UserModel? get currentUser => _currentUser;
  String? get token => _token;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get errorMessage => _errorMessage;
  bool get isAuthenticated => _token != null && _currentUser != null;
  bool get isPolice => _currentUser?.role == 'POLICE';

  Future<void> checkSession() async {
    _token = _storageService.getToken();
    _currentUser = _storageService.getUser();
    _isInitialized = true;
    notifyListeners();

    if (_token != null) {
      try {
        final profileData = await _apiClient.get('/auth/me');
        if (profileData != null) {
          _currentUser = UserModel.fromJson(profileData as Map<String, dynamic>);
          await _storageService.saveSession(
            token: _token!,
            role: _currentUser!.role,
            user: _currentUser!,
          );
          notifyListeners();
        }
      } catch (_) {
        // If profile fetch fails, session may be expired
        if (_storageService.getToken() == null) {
          _token = null;
          _currentUser = null;
          notifyListeners();
        }
      }
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.post('/auth/login', body: {
        'email': email.trim(),
        'password': password,
      });

      final loginRes = LoginResponse.fromJson(response as Map<String, dynamic>);

      // Enforce Police portal role restrictions
      if (loginRes.role != 'POLICE' && loginRes.role != 'ADMIN') {
        _errorMessage = 'Access restricted: Mobile portal is reserved for authorized Police personnel.';
        _isLoading = false;
        notifyListeners();
        return false;
      }

      _token = loginRes.accessToken;
      _currentUser = loginRes.user;

      await _storageService.saveSession(
        token: _token!,
        role: _currentUser!.role,
        user: _currentUser!,
      );

      _isLoading = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'An unexpected connection error occurred.';
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _storageService.clearSession();
    _token = null;
    _currentUser = null;
    _errorMessage = null;
    notifyListeners();
  }
}
