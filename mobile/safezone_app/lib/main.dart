import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'core/api_client.dart';
import 'core/storage_service.dart';
import 'providers/auth_provider.dart';
import 'providers/citizen_provider.dart';
import 'providers/police_provider.dart';
import 'screens/citizen_home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/police_home_screen.dart';
import 'services/location_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final sharedPrefs = await SharedPreferences.getInstance();
  final storageService = StorageService(sharedPrefs);
  final apiClient = ApiClient(storageService);
  final locationService = LocationService();

  runApp(SafeZoneApp(
    storageService: storageService,
    apiClient: apiClient,
    locationService: locationService,
  ));
}

class SafeZoneApp extends StatelessWidget {
  final StorageService storageService;
  final ApiClient apiClient;
  final LocationService locationService;

  const SafeZoneApp({
    super.key,
    required this.storageService,
    required this.apiClient,
    required this.locationService,
  });

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => AuthProvider(apiClient, storageService),
        ),
        ChangeNotifierProvider(
          create: (_) => PoliceProvider(apiClient, storageService, locationService),
        ),
        ChangeNotifierProvider(
          create: (_) => CitizenProvider(apiClient, storageService, locationService),
        ),
      ],
      child: MaterialApp(
        title: 'SafeZone Mobile',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF1E3A8A),
            brightness: Brightness.dark,
          ),
          scaffoldBackgroundColor: const Color(0xFF0F172A),
        ),
        home: const AuthGatekeeper(),
      ),
    );
  }
}

class AuthGatekeeper extends StatelessWidget {
  const AuthGatekeeper({super.key});

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    if (!authProvider.isInitialized) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(
          child: CircularProgressIndicator(color: Color(0xFF3B82F6)),
        ),
      );
    }

    if (authProvider.isAuthenticated) {
      if (authProvider.isPolice) {
        return const PoliceHomeScreen();
      }
      return const CitizenHomeScreen();
    }

    return const LoginScreen();
  }
}
