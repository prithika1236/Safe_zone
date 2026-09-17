import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import '../models/location_status.dart';

/// Device location permissions and coordinates retrieval service.
class LocationService {
  /// Checks service status and prompts for permissions if necessary.
  Future<LocationResult> getCurrentLocation() async {
    try {
      // 1. Check if location services (GPS) are enabled
      final isServiceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!isServiceEnabled) {
        return LocationResult(
          state: LocationPermissionState.serviceDisabled,
          errorMessage: 'Device location services (GPS) are turned off. Please enable GPS in device settings.',
        );
      }

      // 2. Check current permission status
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return LocationResult(
            state: LocationPermissionState.denied,
            errorMessage: 'Location permission was denied. Police patrol dispatch requires location access.',
          );
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return LocationResult(
          state: LocationPermissionState.permanentlyDenied,
          errorMessage: 'Location permission is permanently denied. Please grant location access from device App Settings.',
        );
      }

      // 3. Retrieve current GPS fix
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 10),
      );

      return LocationResult(
        state: LocationPermissionState.granted,
        latitude: position.latitude,
        longitude: position.longitude,
      );
    } catch (e) {
      if (kDebugMode) {
        debugPrint('Location retrieval error occurred');
      }
      return LocationResult(
        state: LocationPermissionState.unavailable,
        errorMessage: 'Unable to obtain GPS fix. Please verify device sensor state.',
      );
    }
  }

  Future<bool> openAppSettings() async {
    return await Geolocator.openAppSettings();
  }

  Future<bool> openLocationSettings() async {
    return await Geolocator.openLocationSettings();
  }
}
