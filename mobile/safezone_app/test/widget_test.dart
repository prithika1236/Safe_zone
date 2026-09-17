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

  testWidgets('SafeZone app launches and displays LoginScreen with Sign In and Sign Up tabs', (WidgetTester tester) async {
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

    // Verify SafeZone Portal branding and tabs exist
    expect(find.text('SafeZone Portal'), findsOneWidget);
    expect(find.text('Sign In'), findsNWidgets(2)); // Tab and Button
    expect(find.text('Citizen Sign Up'), findsOneWidget);
  });

  testWidgets('Switching to Citizen Sign Up tab renders registration fields', (WidgetTester tester) async {
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

    // Tap Citizen Sign Up tab
    final signUpTab = find.text('Citizen Sign Up');
    await tester.tap(signUpTab);
    await tester.pumpAndSettle();

    // Verify register button exists
    expect(find.text('Create Citizen Account'), findsOneWidget);
  });
}
