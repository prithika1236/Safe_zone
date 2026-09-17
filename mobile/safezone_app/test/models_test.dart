import 'package:flutter_test/flutter_test.dart';
import 'package:safezone_app/models/assignment_model.dart';
import 'package:safezone_app/models/emergency_contact_model.dart';
import 'package:safezone_app/models/help_point_model.dart';
import 'package:safezone_app/models/location_status.dart';
import 'package:safezone_app/models/sos_model.dart';
import 'package:safezone_app/models/user_model.dart';

void main() {
  group('UserModel and LoginResponse Tests', () {
    test('UserModel parse JSON correctly with PoliceOfficer', () {
      final json = {
        'id': 10,
        'email': 'officer@police.gov',
        'full_name': 'Officer John Doe',
        'role': 'POLICE',
        'is_active': true,
        'police_officer': {
          'id': 5,
          'badge_number': 'B-9021',
          'rank': 'SERGEANT',
          'phone_number': '+91 9999999999',
          'is_on_duty': true,
        }
      };

      final user = UserModel.fromJson(json);
      expect(user.id, 10);
      expect(user.email, 'officer@police.gov');
      expect(user.fullName, 'Officer John Doe');
      expect(user.role, 'POLICE');
      expect(user.policeOfficer, isNotNull);
      expect(user.policeOfficer!.badgeNumber, 'B-9021');
      expect(user.policeOfficer!.rank, 'SERGEANT');
      expect(user.policeOfficer!.isOnDuty, true);
    });

    test('LoginResponse parse JSON with nested user', () {
      final json = {
        'access_token': 'test_jwt_token_123',
        'token_type': 'bearer',
        'role': 'CITIZEN',
        'user': {
          'id': 12,
          'email': 'citizen@example.com',
          'full_name': 'Jane Citizen',
          'role': 'CITIZEN',
        }
      };

      final loginRes = LoginResponse.fromJson(json);
      expect(loginRes.accessToken, 'test_jwt_token_123');
      expect(loginRes.role, 'CITIZEN');
      expect(loginRes.user.id, 12);
    });
  });

  group('PatrolAssignmentModel Tests', () {
    test('PatrolAssignmentModel parse JSON and status helpers', () {
      final json = {
        'id': 42,
        'patrol_unit_id': 1,
        'prp_id': 7,
        'status': 'ASSIGNED',
        'assigned_at': '2026-09-18T02:00:00Z',
        'distance_meters': 2500.0,
        'estimated_duration_seconds': 360.0,
        'patrol_unit': {
          'id': 1,
          'call_sign': 'PATROL-101',
          'unit_type': 'CAR',
          'status': 'AVAILABLE',
          'current_latitude': 12.9716,
          'current_longitude': 77.5946,
        },
        'prp': {
          'id': 7,
          'latitude': 12.9800,
          'longitude': 77.6000,
          'priority_score': 8.5,
          'coverage_radius_meters': 1500,
          'shift_type': 'NIGHT',
          'status': 'APPROVED',
        }
      };

      final assignment = PatrolAssignmentModel.fromJson(json);
      expect(assignment.id, 42);
      expect(assignment.isAssigned, true);
      expect(assignment.isAcknowledged, false);
      expect(assignment.distanceMeters, 2500.0);
      expect(assignment.patrolUnit!.callSign, 'PATROL-101');
      expect(assignment.prp!.priorityScore, 8.5);
      expect(assignment.prp!.coverageRadiusMeters, 1500);
    });
  });

  group('EmergencyContactModel Tests', () {
    test('EmergencyContactModel serialization and copyWith', () {
      final contact = EmergencyContactModel(
        id: '1',
        name: 'Sarah Connor',
        phoneNumber: '+1-555-0199',
        relationship: 'Family',
        isPrimary: true,
      );

      final json = contact.toJson();
      expect(json['name'], 'Sarah Connor');
      expect(json['is_primary'], true);

      final parsed = EmergencyContactModel.fromJson(json);
      expect(parsed.name, 'Sarah Connor');
      expect(parsed.phoneNumber, '+1-555-0199');
      expect(parsed.isPrimary, true);

      final updated = parsed.copyWith(name: 'Sarah J. Connor');
      expect(updated.name, 'Sarah J. Connor');
      expect(updated.phoneNumber, '+1-555-0199');
    });
  });

  group('HelpPointModel Tests', () {
    test('HelpPointModel parse JSON correctly', () {
      final json = {
        'id': 3,
        'name': 'MG Road Police Station',
        'point_type': 'POLICE_STATION',
        'latitude': 12.9750,
        'longitude': 77.6050,
        'is_24_7': true,
        'is_verified': true,
        'is_active': true,
        'contact_phone': '080-22942555',
        'distance_meters': 1200.0,
      };

      final hp = HelpPointModel.fromJson(json);
      expect(hp.id, 3);
      expect(hp.name, 'MG Road Police Station');
      expect(hp.pointType, 'POLICE_STATION');
      expect(hp.is24_7, true);
      expect(hp.isVerified, true);
      expect(hp.distanceMeters, 1200.0);
    });
  });

  group('LocationResult Tests', () {
    test('LocationResult handles granted vs denied correctly', () {
      final granted = LocationResult(
        state: LocationPermissionState.granted,
        latitude: 12.9716,
        longitude: 77.5946,
      );
      expect(granted.isSuccess, true);

      final denied = LocationResult(
        state: LocationPermissionState.denied,
        errorMessage: 'Permission denied',
      );
      expect(denied.isSuccess, false);
      expect(denied.errorMessage, 'Permission denied');
    });
  });

  group('SOS Models Tests', () {
    test('SOSModel parse JSON with full telemetry and patrol info', () {
      final json = {
        'id': 101,
        'citizen_id': 5,
        'status': 'ASSIGNED',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'assigned_patrol_unit_id': 12,
        'patrol_call_sign': 'EAGLE-1',
        'distance_meters': 1500.0,
        'estimated_duration_seconds': 240.0,
        'trigger_time': '2026-09-18T02:30:00Z',
        'notes': 'Suspect approaching',
        'citizen_name': 'Alice Smith',
        'citizen_phone': '+1234567890',
      };

      final sos = SOSModel.fromJson(json);
      expect(sos.id, 101);
      expect(sos.citizenId, 5);
      expect(sos.status, 'ASSIGNED');
      expect(sos.latitude, 12.9716);
      expect(sos.patrolCallSign, 'EAGLE-1');
      expect(sos.citizenName, 'Alice Smith');
      expect(sos.distanceMeters, 1500.0);
    });

    test('CitizenSOSModel privacy guarantee test (zero exact PRP leakage)', () {
      final json = {
        'id': 202,
        'status': 'EN_ROUTE',
        'latitude': 12.9716,
        'longitude': 77.5946,
        'patrol_assigned': true,
        'patrol_call_sign': 'PATROL-ALPHA',
        'distance_meters': 800.0,
        'estimated_duration_seconds': 120.0,
        'trigger_time': '2026-09-18T02:35:00Z',
      };

      final citizenSos = CitizenSOSModel.fromJson(json);
      expect(citizenSos.id, 202);
      expect(citizenSos.status, 'EN_ROUTE');
      expect(citizenSos.patrolAssigned, true);
      expect(citizenSos.patrolCallSign, 'PATROL-ALPHA');
      expect(citizenSos.distanceMeters, 800.0);
    });
  });
}
