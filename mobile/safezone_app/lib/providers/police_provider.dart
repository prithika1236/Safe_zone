import 'package:flutter/foundation.dart';
import '../core/api_client.dart';
import '../core/storage_service.dart';
import '../models/assignment_model.dart';
import '../models/location_status.dart';
import '../services/location_service.dart';

class PoliceProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final StorageService _storageService;
  final LocationService _locationService;

  PatrolAssignmentModel? _activeAssignment;
  bool _isOnDuty = true;
  LocationResult? _currentLocation;
  bool _isLoading = false;
  bool _isActionInProgress = false;
  String? _errorMessage;
  String? _successMessage;

  PoliceProvider(this._apiClient, this._storageService, this._locationService) {
    _isOnDuty = _storageService.getDutyStatus();
  }

  PatrolAssignmentModel? get activeAssignment => _activeAssignment;
  bool get isOnDuty => _isOnDuty;
  LocationResult? get currentLocation => _currentLocation;
  bool get isLoading => _isLoading;
  bool get isActionInProgress => _isActionInProgress;
  String? get errorMessage => _errorMessage;
  String? get successMessage => _successMessage;

  Future<void> refreshAll() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    await Future.wait([
      fetchCurrentAssignment(silent: true),
      updateLocation(silent: true),
    ]);

    _isLoading = false;
    notifyListeners();
  }

  Future<void> fetchCurrentAssignment({bool silent = false}) async {
    if (!silent) {
      _isLoading = true;
      _errorMessage = null;
      notifyListeners();
    }

    try {
      final response = await _apiClient.get('/police/assignments/current');
      if (response != null && response is Map<String, dynamic>) {
        _activeAssignment = PatrolAssignmentModel.fromJson(response);
      } else {
        _activeAssignment = null;
      }
    } on ApiException catch (e) {
      if (e.statusCode != 404) {
        _errorMessage = e.message;
      } else {
        _activeAssignment = null;
      }
    } catch (_) {
      _errorMessage = 'Failed to load current patrol assignment.';
    } finally {
      if (!silent) {
        _isLoading = false;
        notifyListeners();
      }
    }
  }

  Future<bool> acknowledgeAssignment(int assignmentId) async {
    _isActionInProgress = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.post('/police/assignments/$assignmentId/acknowledge');
      if (response != null && response is Map<String, dynamic>) {
        _activeAssignment = PatrolAssignmentModel.fromJson(response);
      }
      _successMessage = 'Assignment acknowledged. You are now EN ROUTE to PRP.';
      _isActionInProgress = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isActionInProgress = false;
      notifyListeners();
      return false;
    } catch (_) {
      _errorMessage = 'Failed to acknowledge assignment.';
      _isActionInProgress = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> markArrivedAtPRP(int assignmentId) async {
    _isActionInProgress = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.post('/police/assignments/$assignmentId/arrived');
      if (response != null && response is Map<String, dynamic>) {
        _activeAssignment = PatrolAssignmentModel.fromJson(response);
      }
      _successMessage = 'Arrived on-scene at PRP. Deployment active.';
      _isActionInProgress = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isActionInProgress = false;
      notifyListeners();
      return false;
    } catch (_) {
      _errorMessage = 'Failed to mark arrival at PRP.';
      _isActionInProgress = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> completeAssignment(int assignmentId) async {
    _isActionInProgress = true;
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.post('/police/assignments/$assignmentId/complete');
      if (response != null && response is Map<String, dynamic>) {
        _activeAssignment = PatrolAssignmentModel.fromJson(response);
      } else {
        _activeAssignment = null;
      }
      _successMessage = 'Assignment completed. Patrol unit released to AVAILABLE status.';
      _isActionInProgress = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      _isActionInProgress = false;
      notifyListeners();
      return false;
    } catch (_) {
      _errorMessage = 'Failed to complete assignment.';
      _isActionInProgress = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> toggleDutyStatus(bool onDuty) async {
    _isOnDuty = onDuty;
    await _storageService.setDutyStatus(onDuty);
    notifyListeners();
  }

  Future<void> updateLocation({bool silent = false}) async {
    final result = await _locationService.getCurrentLocation();
    _currentLocation = result;
    if (!silent) {
      notifyListeners();
    }
  }

  void clearMessages() {
    _errorMessage = null;
    _successMessage = null;
    notifyListeners();
  }
}
