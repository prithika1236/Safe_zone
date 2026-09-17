class SOSModel {
  final int id;
  final int citizenId;
  final String status;
  final double latitude;
  final double longitude;
  final int? assignedPatrolUnitId;
  final String? patrolCallSign;
  final String? patrolUnitType;
  final double? patrolLatitude;
  final double? patrolLongitude;
  final double? distanceMeters;
  final double? estimatedDurationSeconds;
  final DateTime triggerTime;
  final DateTime? acceptedTime;
  final DateTime? enRouteTime;
  final DateTime? arrivedTime;
  final DateTime? resolvedTime;
  final String? notes;
  final String? citizenName;
  final String? citizenPhone;

  SOSModel({
    required this.id,
    required this.citizenId,
    required this.status,
    required this.latitude,
    required this.longitude,
    this.assignedPatrolUnitId,
    this.patrolCallSign,
    this.patrolUnitType,
    this.patrolLatitude,
    this.patrolLongitude,
    this.distanceMeters,
    this.estimatedDurationSeconds,
    required this.triggerTime,
    this.acceptedTime,
    this.enRouteTime,
    this.arrivedTime,
    this.resolvedTime,
    this.notes,
    this.citizenName,
    this.citizenPhone,
  });

  factory SOSModel.fromJson(Map<String, dynamic> json) {
    return SOSModel(
      id: json['id'] as int,
      citizenId: json['citizen_id'] as int,
      status: json['status'] as String? ?? 'PENDING',
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      assignedPatrolUnitId: json['assigned_patrol_unit_id'] as int?,
      patrolCallSign: json['patrol_call_sign'] as String?,
      patrolUnitType: json['patrol_unit_type'] as String?,
      patrolLatitude: (json['patrol_latitude'] as num?)?.toDouble(),
      patrolLongitude: (json['patrol_longitude'] as num?)?.toDouble(),
      distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
      estimatedDurationSeconds: (json['estimated_duration_seconds'] as num?)?.toDouble(),
      triggerTime: DateTime.parse(json['trigger_time'] as String),
      acceptedTime: json['accepted_time'] != null
          ? DateTime.parse(json['accepted_time'] as String)
          : null,
      enRouteTime: json['en_route_time'] != null
          ? DateTime.parse(json['en_route_time'] as String)
          : null,
      arrivedTime: json['arrived_time'] != null
          ? DateTime.parse(json['arrived_time'] as String)
          : null,
      resolvedTime: json['resolved_time'] != null
          ? DateTime.parse(json['resolved_time'] as String)
          : null,
      notes: json['notes'] as String?,
      citizenName: json['citizen_name'] as String?,
      citizenPhone: json['citizen_phone'] as String?,
    );
  }
}

class CitizenSOSModel {
  final int id;
  final String status;
  final double latitude;
  final double longitude;
  final bool patrolAssigned;
  final String? patrolCallSign;
  final double? distanceMeters;
  final double? estimatedDurationSeconds;
  final DateTime triggerTime;
  final DateTime? acceptedTime;
  final DateTime? enRouteTime;
  final DateTime? arrivedTime;
  final DateTime? resolvedTime;

  CitizenSOSModel({
    required this.id,
    required this.status,
    required this.latitude,
    required this.longitude,
    required this.patrolAssigned,
    this.patrolCallSign,
    this.distanceMeters,
    this.estimatedDurationSeconds,
    required this.triggerTime,
    this.acceptedTime,
    this.enRouteTime,
    this.arrivedTime,
    this.resolvedTime,
  });

  factory CitizenSOSModel.fromJson(Map<String, dynamic> json) {
    return CitizenSOSModel(
      id: json['id'] as int,
      status: json['status'] as String? ?? 'PENDING',
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      patrolAssigned: json['patrol_assigned'] as bool? ?? false,
      patrolCallSign: json['patrol_call_sign'] as String?,
      distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
      estimatedDurationSeconds: (json['estimated_duration_seconds'] as num?)?.toDouble(),
      triggerTime: DateTime.parse(json['trigger_time'] as String),
      acceptedTime: json['accepted_time'] != null
          ? DateTime.parse(json['accepted_time'] as String)
          : null,
      enRouteTime: json['en_route_time'] != null
          ? DateTime.parse(json['en_route_time'] as String)
          : null,
      arrivedTime: json['arrived_time'] != null
          ? DateTime.parse(json['arrived_time'] as String)
          : null,
      resolvedTime: json['resolved_time'] != null
          ? DateTime.parse(json['resolved_time'] as String)
          : null,
    );
  }
}
