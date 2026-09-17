class PRPLocationModel {
  final int id;
  final double latitude;
  final double longitude;
  final double? priorityScore;
  final int coverageRadiusMeters;
  final String shiftType;
  final String status;

  PRPLocationModel({
    required this.id,
    required this.latitude,
    required this.longitude,
    this.priorityScore,
    required this.coverageRadiusMeters,
    required this.shiftType,
    required this.status,
  });

  factory PRPLocationModel.fromJson(Map<String, dynamic> json) {
    return PRPLocationModel(
      id: json['id'] as int,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      priorityScore: json['priority_score'] != null
          ? (json['priority_score'] as num).toDouble()
          : null,
      coverageRadiusMeters: json['coverage_radius_meters'] as int? ?? 1500,
      shiftType: json['shift_type'] as String? ?? 'NIGHT',
      status: json['status'] as String? ?? 'APPROVED',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'latitude': latitude,
      'longitude': longitude,
      'priority_score': priorityScore,
      'coverage_radius_meters': coverageRadiusMeters,
      'shift_type': shiftType,
      'status': status,
    };
  }
}

class PatrolUnitSummaryModel {
  final int id;
  final String callSign;
  final String unitType;
  final String status;
  final double? currentLatitude;
  final double? currentLongitude;

  PatrolUnitSummaryModel({
    required this.id,
    required this.callSign,
    required this.unitType,
    required this.status,
    this.currentLatitude,
    this.currentLongitude,
  });

  factory PatrolUnitSummaryModel.fromJson(Map<String, dynamic> json) {
    return PatrolUnitSummaryModel(
      id: json['id'] as int,
      callSign: json['call_sign'] as String? ?? '',
      unitType: json['unit_type'] as String? ?? 'CAR',
      status: json['status'] as String? ?? 'AVAILABLE',
      currentLatitude: json['current_latitude'] != null
          ? (json['current_latitude'] as num).toDouble()
          : null,
      currentLongitude: json['current_longitude'] != null
          ? (json['current_longitude'] as num).toDouble()
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'call_sign': callSign,
      'unit_type': unitType,
      'status': status,
      'current_latitude': currentLatitude,
      'current_longitude': currentLongitude,
    };
  }
}

class PatrolAssignmentModel {
  final int id;
  final int patrolUnitId;
  final int prpId;
  final String status; // ASSIGNED, ACKNOWLEDGED, ARRIVED, COMPLETED, CANCELLED
  final String assignedAt;
  final String? acknowledgedAt;
  final String? arrivedAt;
  final String? completedAt;
  final double? distanceMeters;
  final double? estimatedDurationSeconds;
  final PatrolUnitSummaryModel? patrolUnit;
  final PRPLocationModel? prp;

  PatrolAssignmentModel({
    required this.id,
    required this.patrolUnitId,
    required this.prpId,
    required this.status,
    required this.assignedAt,
    this.acknowledgedAt,
    this.arrivedAt,
    this.completedAt,
    this.distanceMeters,
    this.estimatedDurationSeconds,
    this.patrolUnit,
    this.prp,
  });

  factory PatrolAssignmentModel.fromJson(Map<String, dynamic> json) {
    return PatrolAssignmentModel(
      id: json['id'] as int,
      patrolUnitId: json['patrol_unit_id'] as int,
      prpId: json['prp_id'] as int,
      status: json['status'] as String? ?? 'ASSIGNED',
      assignedAt: json['assigned_at'] as String? ?? '',
      acknowledgedAt: json['acknowledged_at'] as String?,
      arrivedAt: json['arrived_at'] as String?,
      completedAt: json['completed_at'] as String?,
      distanceMeters: json['distance_meters'] != null
          ? (json['distance_meters'] as num).toDouble()
          : null,
      estimatedDurationSeconds: json['estimated_duration_seconds'] != null
          ? (json['estimated_duration_seconds'] as num).toDouble()
          : null,
      patrolUnit: json['patrol_unit'] != null
          ? PatrolUnitSummaryModel.fromJson(
              json['patrol_unit'] as Map<String, dynamic>)
          : null,
      prp: json['prp'] != null
          ? PRPLocationModel.fromJson(json['prp'] as Map<String, dynamic>)
          : null,
    );
  }

  bool get isAssigned => status == 'ASSIGNED';
  bool get isAcknowledged => status == 'ACKNOWLEDGED';
  bool get isArrived => status == 'ARRIVED';
  bool get isCompleted => status == 'COMPLETED';
}
