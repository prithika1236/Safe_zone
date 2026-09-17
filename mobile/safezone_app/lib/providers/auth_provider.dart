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
  String? _successMessage;

  AuthProvider(this._apiClient, this._storageService) {
    checkSession();
  }

  UserModel? get currentUser => _currentUser;
  String? get token => _token;
  bool get isLoading => _isLoading;
  bool get isInitialized => _isInitialized;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;
  bool get isAuthenticated => _token != null && _currentUser != null;
  bool get isPolice => _currentUser?.role == 'POLICE';
  bool get isCitizen => _currentUser?.role == 'CITIZEN' || _currentUser?.role == 'ADMIN';

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
    _successMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.post('/auth/login', body: {
        'email': email.trim(),
        'password': password,
      });

      final loginRes = LoginResponse.fromJson(response as Map<String, dynamic>);

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

  Future<bool> register({
    required String email,
    required String password,
    required String fullName,
    String? phoneNumber,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      await _apiClient.post('/auth/register', body: {
        'email': email.trim(),
        'password': password,
        'full_name': fullName.trim(),
        'phone_number': phoneNumber?.trim().isNotEmpty == true ? phoneNumber!.trim() : null,
        'role': 'CITIZEN',
      });

      _successMessage = 'Account created successfully! Please sign in.';
      _isLoading = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isLoading = false;
      notifyListeners();
      return false;
    } catch (e) {
      _errorMessage = 'Unable to register citizen account. Please check network.';
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
    _successMessage = null;
    notifyListeners();
  }

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }
}
