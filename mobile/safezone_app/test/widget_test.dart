import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:safezone_app/core/api_client.dart';
import 'package:safezone_app/core/storage_service.dart';
import 'package:safezone_app/main.dart';
import 'package:safezone_app/services/location_service.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('SafeZone app launches and displays LoginScreen by default', (WidgetTester tester) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final apiClient = ApiClient(storage);
    final locationService = LocationService();

    await tester.pumpWidget(SafeZoneApp(
      storageService: storage,
      apiClient: apiClient,
      locationService: locationService,
    ));

    await tester.pumpAndSettle();

    // Verify Police Portal branding and login inputs exist
    expect(find.text('SafeZone Police Portal'), findsOneWidget);
    expect(find.text('Sign In to Terminal'), findsOneWidget);
    expect(find.byType(TextFormField), findsNWidgets(2));
  });

  testWidgets('Login form validation triggers on empty input', (WidgetTester tester) async {
    final prefs = await SharedPreferences.getInstance();
    final storage = StorageService(prefs);
    final apiClient = ApiClient(storage);
    final locationService = LocationService();

    await tester.pumpWidget(SafeZoneApp(
      storageService: storage,
      apiClient: apiClient,
      locationService: locationService,
    ));

    await tester.pumpAndSettle();

    // Tap submit button without entering credentials
    final submitButton = find.text('Sign In to Terminal');
    await tester.tap(submitButton);
    await tester.pumpAndSettle();

    // Verify validation errors appear
    expect(find.text('Please enter officer email'), findsOneWidget);
    expect(find.text('Please enter password'), findsOneWidget);
  });
}
