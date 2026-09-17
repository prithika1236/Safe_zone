import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../models/emergency_contact_model.dart';
import '../models/help_point_model.dart';
import '../models/location_status.dart';
import '../providers/auth_provider.dart';
import '../providers/citizen_provider.dart';
import '../services/location_service.dart';
import 'sos_status_screen.dart';

class CitizenHomeScreen extends StatefulWidget {
  const CitizenHomeScreen({super.key});

  @override
  State<CitizenHomeScreen> createState() => _CitizenHomeScreenState();
}

class _CitizenHomeScreenState extends State<CitizenHomeScreen> {
  final MapController _mapController = MapController();
  final LocationService _locationService = LocationService();
  bool _isMapView = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final citizenProvider = Provider.of<CitizenProvider>(context, listen: false);
      citizenProvider.refreshAll();
    });
  }

  void _triggerEmergencySOS() {
    final citizenProvider = Provider.of<CitizenProvider>(context, listen: false);
    citizenProvider.triggerSOS();
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const SOSStatusScreen()),
    );
  }

  void _showAddEditContactDialog({EmergencyContactModel? existing}) {
    final nameCtrl = TextEditingController(text: existing?.name ?? '');
    final phoneCtrl = TextEditingController(text: existing?.phoneNumber ?? '');
    String relationship = existing?.relationship ?? 'Family';
    bool isPrimary = existing?.isPrimary ?? false;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    existing == null ? 'Add Emergency Contact' : 'Edit Contact',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: nameCtrl,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'Contact Name',
                      labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                      filled: true,
                      fillColor: const Color(0xFF0F172A),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: phoneCtrl,
                    keyboardType: TextInputType.phone,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'Phone Number',
                      labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                      filled: true,
                      fillColor: const Color(0xFF0F172A),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: relationship,
                    dropdownColor: const Color(0xFF0F172A),
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'Relationship',
                      labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                      filled: true,
                      fillColor: const Color(0xFF0F172A),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    items: ['Family', 'Friend', 'Spouse', 'Parent', 'Other']
                        .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                        .toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setModalState(() => relationship = val);
                      }
                    },
                  ),
                  const SizedBox(height: 8),
                  CheckboxListTile(
                    title: const Text('Primary Contact (Priority notification)',
                        style: TextStyle(color: Colors.white, fontSize: 13)),
                    value: isPrimary,
                    activeColor: const Color(0xFF38BDF8),
                    checkColor: Colors.black,
                    contentPadding: EdgeInsets.zero,
                    onChanged: (val) {
                      setModalState(() => isPrimary = val ?? false);
                    },
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(ctx).pop(),
                        child: const Text('Cancel', style: TextStyle(color: Color(0xFF94A3B8))),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF2563EB),
                          foregroundColor: Colors.white,
                        ),
                        onPressed: () {
                          if (nameCtrl.text.trim().isEmpty || phoneCtrl.text.trim().isEmpty) return;
                          final provider = Provider.of<CitizenProvider>(context, listen: false);
                          if (existing == null) {
                            provider.addEmergencyContact(
                              name: nameCtrl.text,
                              phoneNumber: phoneCtrl.text,
                              relationship: relationship,
                              isPrimary: isPrimary,
                            );
                          } else {
                            provider.updateEmergencyContact(existing.copyWith(
                              name: nameCtrl.text,
                              phoneNumber: phoneCtrl.text,
                              relationship: relationship,
                              isPrimary: isPrimary,
                            ));
                          }
                          Navigator.of(ctx).pop();
                        },
                        child: Text(existing == null ? 'Save Contact' : 'Update'),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final citizenProvider = Provider.of<CitizenProvider>(context);
    final location = citizenProvider.currentLocation;
    final helpPoints = citizenProvider.helpPoints;
    final contacts = citizenProvider.emergencyContacts;

    const LatLng defaultCenter = LatLng(12.9716, 77.5946);
    final LatLng userLatLng = (location?.latitude != null && location?.longitude != null)
        ? LatLng(location!.latitude!, location.longitude!)
        : defaultCenter;

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFF059669),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(Icons.shield_outlined, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  authProvider.currentUser?.fullName ?? 'SafeZone Citizen',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  location?.isSuccess == true ? '📍 Location Active' : '⚠️ Location Pending',
                  style: TextStyle(
                    fontSize: 11,
                    color: location?.isSuccess == true
                        ? const Color(0xFF34D399)
                        : const Color(0xFFFBBF24),
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, color: Color(0xFF94A3B8)),
            tooltip: 'Sign Out',
            onPressed: () => authProvider.logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => citizenProvider.refreshAll(),
        color: const Color(0xFF3B82F6),
        backgroundColor: const Color(0xFF1E293B),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Location Warning Banner if needed
            if (location != null && location.state != LocationPermissionState.granted)
              _buildLocationWarning(location),

            // 1. Prominent Central SOS Panic Button
            _buildSOSSection(),

            const SizedBox(height: 24),

            // 2. Emergency Contacts Section
            _buildContactsSection(contacts),

            const SizedBox(height: 24),

            // 3. Verified Safe Help Points Map/List Section
            _buildHelpPointsSection(userLatLng, helpPoints, citizenProvider.isLoadingHelpPoints),
          ],
        ),
      ),
    );
  }

  Widget _buildLocationWarning(LocationResult location) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF451A03),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFF59E0B)),
      ),
      child: Row(
        children: [
          const Icon(Icons.location_off, color: Color(0xFFFBBF24), size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              location.errorMessage ?? 'Please enable GPS for automatic SOS emergency positioning.',
              style: const TextStyle(color: Color(0xFFFEF3C7), fontSize: 12),
            ),
          ),
          ElevatedButton(
            onPressed: () => _locationService.openLocationSettings(),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFF59E0B),
              foregroundColor: Colors.black,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
            child: const Text('Enable GPS'),
          ),
        ],
      ),
    );
  }

  Widget _buildSOSSection() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF881337)),
      ),
      child: Column(
        children: [
          const Text(
            'EMERGENCY PANIC TRIGGER',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.2,
              color: Color(0xFFFDA4AF),
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Instantly broadcasts live coordinates to dispatch & emergency contacts',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
          ),
          const SizedBox(height: 20),

          // Glowing Pulsing SOS Button
          GestureDetector(
            onTap: _triggerEmergencySOS,
            child: Container(
              width: 130,
              height: 130,
              decoration: BoxDecoration(
                gradient: const RadialGradient(
                  colors: [Color(0xFFF43F5E), Color(0xFFBE123C)],
                  radius: 0.85,
                ),
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFFF43F5E).withValues(alpha: 0.4),
                    blurRadius: 28,
                    spreadRadius: 6,
                  ),
                ],
              ),
              child: const Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.touch_app, size: 38, color: Colors.white),
                  SizedBox(height: 4),
                  Text(
                    'SOS',
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContactsSection(List<EmergencyContactModel> contacts) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.contacts_outlined, color: Color(0xFF38BDF8), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Emergency Contacts',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              ElevatedButton.icon(
                icon: const Icon(Icons.add, size: 14),
                label: const Text('Add Contact', style: TextStyle(fontSize: 11)),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                ),
                onPressed: () => _showAddEditContactDialog(),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (contacts.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF0F172A),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Center(
                child: Text(
                  'No emergency contacts configured yet. Add trusted contacts who will be notified during panic triggers.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                ),
              ),
            )
          else
            ...contacts.map(
              (c) => Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: c.isPrimary ? const Color(0xFF38BDF8) : const Color(0xFF334155),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.person, color: Color(0xFF94A3B8), size: 18),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Text(
                                c.name,
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                  fontSize: 13,
                                ),
                              ),
                              if (c.isPrimary) ...[
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF0369A1),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: const Text('PRIMARY', style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.white)),
                                ),
                              ],
                            ],
                          ),
                          Text(
                            '${c.phoneNumber} • ${c.relationship}',
                            style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.edit_outlined, size: 16, color: Color(0xFF94A3B8)),
                      onPressed: () => _showAddEditContactDialog(existing: c),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 16, color: Color(0xFFF43F5E)),
                      onPressed: () => Provider.of<CitizenProvider>(context, listen: false).deleteEmergencyContact(c.id),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHelpPointsSection(LatLng userLatLng, List<HelpPointModel> helpPoints, bool isLoading) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.location_city_outlined, color: Color(0xFFA855F7), size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Nearby Safe Help Points',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              Row(
                children: [
                  IconButton(
                    icon: Icon(Icons.map_outlined, color: _isMapView ? const Color(0xFFA855F7) : const Color(0xFF94A3B8)),
                    onPressed: () => setState(() => _isMapView = true),
                  ),
                  IconButton(
                    icon: Icon(Icons.list_alt_outlined, color: !_isMapView ? const Color(0xFFA855F7) : const Color(0xFF94A3B8)),
                    onPressed: () => setState(() => _isMapView = false),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (isLoading)
            const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator(color: Color(0xFFA855F7))))
          else if (_isMapView)
            Container(
              height: 240,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              clipBehavior: Clip.antiAlias,
              child: FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: userLatLng,
                  initialZoom: 13.0,
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'com.safezone.safezone_app',
                  ),
                  MarkerLayer(
                    markers: [
                      // User location marker
                      Marker(
                        point: userLatLng,
                        width: 32,
                        height: 32,
                        child: Container(
                          decoration: BoxDecoration(
                            color: const Color(0xFF2563EB),
                            shape: BoxShape.circle,
                            border: Border.all(color: Colors.white, width: 2),
                          ),
                          child: const Icon(Icons.person_pin_circle, color: Colors.white, size: 18),
                        ),
                      ),
                      // Safe Help Points (Purple) - ZERO PRPs displayed
                      ...helpPoints.map(
                        (hp) => Marker(
                          point: LatLng(hp.latitude, hp.longitude),
                          width: 32,
                          height: 32,
                          child: Container(
                            decoration: BoxDecoration(
                              color: const Color(0xFF9333EA),
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 1.5),
                            ),
                            child: const Icon(Icons.local_hospital, color: Colors.white, size: 16),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            )
          else
            Column(
              children: [
                if (helpPoints.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No verified Safe Help Points found nearby.', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                  )
                else
                  ...helpPoints.map(
                    (hp) => Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  hp.name,
                                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 13),
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  '${hp.pointType} • ${hp.is24_7 ? "24/7 Open" : "Standard Hours"}${hp.distanceMeters != null ? " • ${(hp.distanceMeters! / 1000).toStringAsFixed(1)} km away" : ""}',
                                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                                ),
                              ],
                            ),
                          ),
                          if (hp.contactPhone != null)
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: const Color(0xFF1E293B),
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: const Color(0xFFA855F7)),
                              ),
                              child: Text(
                                hp.contactPhone!,
                                style: const TextStyle(color: Color(0xFFE9D5FF), fontSize: 11, fontWeight: FontWeight.bold),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}
