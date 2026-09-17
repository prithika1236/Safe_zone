class PoliceOfficerModel {
  final int id;
  final String badgeNumber;
  final String rank;
  final String? phoneNumber;
  final bool isOnDuty;

  PoliceOfficerModel({
    required this.id,
    required this.badgeNumber,
    required this.rank,
    this.phoneNumber,
    this.isOnDuty = true,
  });

  factory PoliceOfficerModel.fromJson(Map<String, dynamic> json) {
    return PoliceOfficerModel(
      id: json['id'] as int,
      badgeNumber: json['badge_number'] as String? ?? '',
      rank: json['rank'] as String? ?? 'OFFICER',
      phoneNumber: json['phone_number'] as String?,
      isOnDuty: json['is_on_duty'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'badge_number': badgeNumber,
      'rank': rank,
      'phone_number': phoneNumber,
      'is_on_duty': isOnDuty,
    };
  }
}

class UserModel {
  final int id;
  final String email;
  final String fullName;
  final String role;
  final bool isActive;
  final PoliceOfficerModel? policeOfficer;

  UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    this.isActive = true,
    this.policeOfficer,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as int,
      email: json['email'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      role: json['role'] as String? ?? 'CITIZEN',
      isActive: json['is_active'] as bool? ?? true,
      policeOfficer: json['police_officer'] != null
          ? PoliceOfficerModel.fromJson(
              json['police_officer'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      'is_active': isActive,
      'police_officer': policeOfficer?.toJson(),
    };
  }
}

class LoginResponse {
  final String accessToken;
  final String tokenType;
  final String role;
  final UserModel user;

  LoginResponse({
    required this.accessToken,
    required this.tokenType,
    required this.role,
    required this.user,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      accessToken: json['access_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      role: json['role'] as String,
      user: UserModel.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
