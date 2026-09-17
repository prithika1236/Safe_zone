class HelpPointModel {
  final int id;
  final String name;
  final String pointType;
  final double latitude;
  final double longitude;
  final String? address;
  final String? contactPhone;
  final bool is24_7;
  final bool isVerified;
  final bool isActive;
  final double? distanceMeters;

  HelpPointModel({
    required this.id,
    required this.name,
    required this.pointType,
    required this.latitude,
    required this.longitude,
    this.address,
    this.contactPhone,
    this.is24_7 = true,
    this.isVerified = true,
    this.isActive = true,
    this.distanceMeters,
  });

  factory HelpPointModel.fromJson(Map<String, dynamic> json) {
    return HelpPointModel(
      id: json['id'] as int,
      name: json['name'] as String? ?? 'Safe Help Point',
      pointType: json['point_type'] as String? ?? 'OTHER',
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      address: json['address'] as String?,
      contactPhone: json['contact_phone'] as String?,
      is24_7: json['is_24_7'] as bool? ?? true,
      isVerified: json['is_verified'] as bool? ?? true,
      isActive: json['is_active'] as bool? ?? true,
      distanceMeters: json['distance_meters'] != null
          ? (json['distance_meters'] as num).toDouble()
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'point_type': pointType,
      'latitude': latitude,
      'longitude': longitude,
      'address': address,
      'contact_phone': contactPhone,
      'is_24_7': is24_7,
      'is_verified': isVerified,
      'is_active': isActive,
      'distance_meters': distanceMeters,
    };
  }
}
