import 'package:flutter/foundation.dart';
import '../core/api_client.dart';
import '../core/storage_service.dart';
import '../models/emergency_contact_model.dart';
import '../models/help_point_model.dart';
import '../models/location_status.dart';
import '../models/sos_model.dart';
import '../services/location_service.dart';

class CitizenProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final StorageService _storageService;
  final LocationService _locationService;

  List<HelpPointModel> _helpPoints = [];
  List<EmergencyContactModel> _emergencyContacts = [];
  LocationResult? _currentLocation;
  CitizenSOSModel? _activeSOS;

  bool _isLoadingHelpPoints = false;
  bool _isSOSTriggered = false;
  DateTime? _sosTriggeredAt;
  String _sosStatus = 'READY'; // READY, PENDING, ASSIGNED, ACCEPTED, EN_ROUTE, ARRIVED, RESOLVED, CANCELLED
  String? _errorMessage;

  CitizenProvider(this._apiClient, this._storageService, this._locationService) {
    _emergencyContacts = _storageService.getEmergencyContacts();
  }

  List<HelpPointModel> get helpPoints => _helpPoints;
  List<EmergencyContactModel> get emergencyContacts => _emergencyContacts;
  LocationResult? get currentLocation => _currentLocation;
  CitizenSOSModel? get activeSOS => _activeSOS;
  bool get isLoadingHelpPoints => _isLoadingHelpPoints;
  bool get isSOSTriggered => _isSOSTriggered;
  DateTime? get sosTriggeredAt => _sosTriggeredAt;
  String get sosStatus => _sosStatus;
  String? get errorMessage => _errorMessage;

  Future<void> refreshAll() async {
    await Future.wait([
      updateLocation(),
      loadEmergencyContacts(),
      fetchActiveSOS(),
    ]);

    if (_currentLocation?.isSuccess == true) {
      await fetchNearbyHelpPoints(
        latitude: _currentLocation!.latitude!,
        longitude: _currentLocation!.longitude!,
      );
    } else {
      await fetchNearbyHelpPoints();
    }
  }

  Future<void> updateLocation() async {
    _currentLocation = await _locationService.getCurrentLocation();
    notifyListeners();
  }

  Future<void> fetchNearbyHelpPoints({
    double latitude = 12.9716,
    double longitude = 77.5946,
    double radiusKm = 10.0,
  }) async {
    _isLoadingHelpPoints = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.get(
        '/help-points/nearby',
        queryParams: {
          'latitude': latitude,
          'longitude': longitude,
          'radius_km': radiusKm,
          'page_size': 50,
        },
      );

      if (response != null && response is Map<String, dynamic>) {
        final items = response['items'] as List<dynamic>? ?? [];
        _helpPoints = items
            .map((item) => HelpPointModel.fromJson(item as Map<String, dynamic>))
            .toList();
      }
    } on ApiException catch (e) {
      // Fallback to general help-points if nearby query fails
      try {
        final fallback = await _apiClient.get('/help-points', queryParams: {'page_size': 50});
        if (fallback != null && fallback is Map<String, dynamic>) {
          final items = fallback['items'] as List<dynamic>? ?? [];
          _helpPoints = items
              .map((item) => HelpPointModel.fromJson(item as Map<String, dynamic>))
              .toList();
        }
      } catch (_) {
        _errorMessage = e.message;
      }
    } catch (_) {
      _errorMessage = 'Failed to load Safe Help Points.';
    } finally {
      _isLoadingHelpPoints = false;
      notifyListeners();
    }
  }

  // --- Emergency Contacts CRUD ---

  Future<void> loadEmergencyContacts() async {
    _emergencyContacts = _storageService.getEmergencyContacts();
    notifyListeners();
  }

  Future<void> addEmergencyContact({
    required String name,
    required String phoneNumber,
    required String relationship,
    bool isPrimary = false,
  }) async {
    final newContact = EmergencyContactModel(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: name.trim(),
      phoneNumber: phoneNumber.trim(),
      relationship: relationship.trim(),
      isPrimary: isPrimary,
    );

    _emergencyContacts.add(newContact);
    await _storageService.saveEmergencyContacts(_emergencyContacts);
    notifyListeners();
  }

  Future<void> updateEmergencyContact(EmergencyContactModel contact) async {
    final idx = _emergencyContacts.indexWhere((c) => c.id == contact.id);
    if (idx != -1) {
      _emergencyContacts[idx] = contact;
      await _storageService.saveEmergencyContacts(_emergencyContacts);
      notifyListeners();
    }
  }

  Future<void> deleteEmergencyContact(String id) async {
    _emergencyContacts.removeWhere((c) => c.id == id);
    await _storageService.saveEmergencyContacts(_emergencyContacts);
    notifyListeners();
  }

  // --- SOS Panic Operations ---

  Future<void> fetchActiveSOS() async {
    try {
      final response = await _apiClient.get('/sos/active');
      if (response != null && response is Map<String, dynamic>) {
        _activeSOS = CitizenSOSModel.fromJson(response);
        _isSOSTriggered = true;
        _sosTriggeredAt = _activeSOS!.triggerTime;
        _sosStatus = _activeSOS!.status;
      } else {
        _activeSOS = null;
        _isSOSTriggered = false;
        _sosStatus = 'READY';
      }
    } catch (_) {
      // No active SOS or unauthenticated
    }
    notifyListeners();
  }

  Future<bool> triggerSOS({String? notes}) async {
    _isSOSTriggered = true;
    _sosTriggeredAt = DateTime.now();
    _sosStatus = 'PENDING';
    _errorMessage = null;
    notifyListeners();

    // Ensure we have current GPS coordinates
    await updateLocation();

    final lat = _currentLocation?.latitude ?? 12.9716;
    final lon = _currentLocation?.longitude ?? 77.5946;

    try {
      final response = await _apiClient.post('/sos/trigger', body: {
        'latitude': lat,
        'longitude': lon,
        'notes': notes,
      });

      if (response != null && response is Map<String, dynamic>) {
        _activeSOS = CitizenSOSModel.fromJson(response);
        _sosStatus = _activeSOS!.status;
        notifyListeners();
        return true;
      }
      return false;
    } on ApiException catch (e) {
      _errorMessage = e.message;
      notifyListeners();
      return false;
    } catch (_) {
      _errorMessage = 'Emergency distress signal transmission failed.';
      notifyListeners();
      return false;
    }
  }

  Future<bool> cancelSOS() async {
    if (_activeSOS != null) {
      try {
        await _apiClient.post('/sos/${_activeSOS!.id}/cancel');
      } catch (_) {}
    }
    _isSOSTriggered = false;
    _activeSOS = null;
    _sosTriggeredAt = null;
    _sosStatus = 'READY';
    notifyListeners();
    return true;
  }
}
