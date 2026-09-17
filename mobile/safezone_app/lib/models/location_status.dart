enum LocationPermissionState {
  granted,
  denied,
  permanentlyDenied,
  serviceDisabled,
  unavailable,
}

class LocationResult {
  final LocationPermissionState state;
  final double? latitude;
  final double? longitude;
  final String? errorMessage;

  LocationResult({
    required this.state,
    this.latitude,
    this.longitude,
    this.errorMessage,
  });

  bool get isSuccess => state == LocationPermissionState.granted && latitude != null && longitude != null;
}
