class EmergencyContactModel {
  final String id;
  final String name;
  final String phoneNumber;
  final String relationship;
  final bool isPrimary;

  EmergencyContactModel({
    required this.id,
    required this.name,
    required this.phoneNumber,
    required this.relationship,
    this.isPrimary = false,
  });

  factory EmergencyContactModel.fromJson(Map<String, dynamic> json) {
    return EmergencyContactModel(
      id: json['id']?.toString() ?? DateTime.now().millisecondsSinceEpoch.toString(),
      name: json['name'] as String? ?? '',
      phoneNumber: json['phone_number'] as String? ?? '',
      relationship: json['relationship'] as String? ?? 'Family',
      isPrimary: json['is_primary'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'phone_number': phoneNumber,
      'relationship': relationship,
      'is_primary': isPrimary,
    };
  }

  EmergencyContactModel copyWith({
    String? id,
    String? name,
    String? phoneNumber,
    String? relationship,
    bool? isPrimary,
  }) {
    return EmergencyContactModel(
      id: id ?? this.id,
      name: name ?? this.name,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      relationship: relationship ?? this.relationship,
      isPrimary: isPrimary ?? this.isPrimary,
    );
  }
}
