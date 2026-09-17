import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:safezone_app/core/api_client.dart';
import 'package:safezone_app/core/storage_service.dart';
import 'package:safezone_app/providers/citizen_provider.dart';
import 'package:safezone_app/services/location_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  test('CitizenProvider emergency contacts CRUD', () async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final apiClient = ApiClient(storage);
    final locationService = LocationService();

    final provider = CitizenProvider(apiClient, storage, locationService);

    expect(provider.emergencyContacts.length, 0);

    // Add contact
    await provider.addEmergencyContact(
      name: 'Dr. John Watson',
      phoneNumber: '+44 20 7946 0991',
      relationship: 'Friend',
      isPrimary: true,
    );

    expect(provider.emergencyContacts.length, 1);
    expect(provider.emergencyContacts.first.name, 'Dr. John Watson');
    expect(provider.emergencyContacts.first.isPrimary, true);

    // Edit contact
    final created = provider.emergencyContacts.first;
    await provider.updateEmergencyContact(created.copyWith(name: 'Dr. Watson'));
    expect(provider.emergencyContacts.first.name, 'Dr. Watson');

    // Delete contact
    await provider.deleteEmergencyContact(created.id);
    expect(provider.emergencyContacts.length, 0);
  });

  test('CitizenProvider SOS trigger and cancel lifecycle', () async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final apiClient = ApiClient(storage);
    final locationService = LocationService();

    final provider = CitizenProvider(apiClient, storage, locationService);

    expect(provider.isSOSTriggered, false);
    expect(provider.sosStatus, 'READY');

    // Trigger SOS
    await provider.triggerSOS();
    expect(provider.isSOSTriggered, true);
    expect(provider.sosTriggeredAt, isNotNull);

    // Cancel SOS
    provider.cancelSOS();
    expect(provider.isSOSTriggered, false);
    expect(provider.sosStatus, 'READY');
  });
}
