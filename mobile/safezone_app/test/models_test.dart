import 'package:flutter_test/flutter_test.dart';
import 'package:safezone_app/models/assignment_model.dart';
import 'package:safezone_app/models/location_status.dart';
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
        'role': 'POLICE',
        'user': {
          'id': 10,
          'email': 'officer@police.gov',
          'full_name': 'Officer John Doe',
          'role': 'POLICE',
        }
      };

      final loginRes = LoginResponse.fromJson(json);
      expect(loginRes.accessToken, 'test_jwt_token_123');
      expect(loginRes.role, 'POLICE');
      expect(loginRes.user.id, 10);
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
}
