import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../models/assignment_model.dart';
import '../models/location_status.dart';
import '../providers/auth_provider.dart';
import '../providers/police_provider.dart';
import '../services/location_service.dart';

class PoliceHomeScreen extends StatefulWidget {
  const PoliceHomeScreen({super.key});

  @override
  State<PoliceHomeScreen> createState() => _PoliceHomeScreenState();
}

class _PoliceHomeScreenState extends State<PoliceHomeScreen> {
  final MapController _mapController = MapController();
  final LocationService _locationService = LocationService();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final policeProvider = Provider.of<PoliceProvider>(context, listen: false);
      policeProvider.refreshAll();
    });
  }

  void _recenterMap(LatLng target) {
    _mapController.move(target, 14.5);
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final policeProvider = Provider.of<PoliceProvider>(context);
    final officer = authProvider.currentUser?.policeOfficer;
    final assignment = policeProvider.activeAssignment;
    final location = policeProvider.currentLocation;

    const LatLng defaultCenter = LatLng(12.9716, 77.5946);
    final LatLng? officerLatLng = (location?.latitude != null && location?.longitude != null)
        ? LatLng(location!.latitude!, location.longitude!)
        : null;
    final LatLng? prpLatLng = (assignment?.prp != null)
        ? LatLng(assignment!.prp!.latitude, assignment.prp!.longitude)
        : null;

    final LatLng mapCenter = prpLatLng ?? officerLatLng ?? defaultCenter;

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
                color: const Color(0xFF1E3A8A),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(Icons.shield, color: Colors.white, size: 20),
            ),
            const SizedBox(width: 10),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  authProvider.currentUser?.fullName ?? 'Police Officer',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                Text(
                  'Badge: ${officer?.badgeNumber ?? "N/A"} • ${officer?.rank ?? "OFFICER"}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFF94A3B8),
                  ),
                ),
              ],
            ),
          ],
        ),
        actions: [
          // On Duty switch
          Row(
            children: [
              Text(
                policeProvider.isOnDuty ? 'ON DUTY' : 'OFF DUTY',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: policeProvider.isOnDuty
                      ? const Color(0xFF34D399)
                      : const Color(0xFF94A3B8),
                ),
              ),
              Switch(
                value: policeProvider.isOnDuty,
                activeTrackColor: const Color(0xFF10B981),
                onChanged: (val) {
                  policeProvider.toggleDutyStatus(val);
                },
              ),
            ],
          ),
          IconButton(
            icon: const Icon(Icons.logout, color: Color(0xFF94A3B8)),
            tooltip: 'Sign Out',
            onPressed: () => authProvider.logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => policeProvider.refreshAll(),
        color: const Color(0xFF3B82F6),
        backgroundColor: const Color(0xFF1E293B),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // 1. Location Status / Permission Alert Banner
            if (location != null && location.state != LocationPermissionState.granted)
              _buildLocationWarningBanner(location),

            // 2. Success / Error Feedback Snackbars
            if (policeProvider.errorMessage != null)
              _buildAlertBanner(
                message: policeProvider.errorMessage!,
                isError: true,
                onDismiss: () => policeProvider.clearMessages(),
              ),

            if (policeProvider.successMessage != null)
              _buildAlertBanner(
                message: policeProvider.successMessage!,
                isError: false,
                onDismiss: () => policeProvider.clearMessages(),
              ),

            // 3. Active PRP Assignment Card
            _buildAssignmentCard(policeProvider, assignment),

            const SizedBox(height: 16),

            // 4. Interactive Tactical Map Container
            _buildMapSection(mapCenter, officerLatLng, prpLatLng, assignment),

            const SizedBox(height: 16),

            // 5. Emergency SOS Monitoring Placeholder Card
            _buildSOSPlaceholderCard(),
          ],
        ),
      ),
    );
  }

  Widget _buildLocationWarningBanner(LocationResult location) {
    String title = 'Location Alert';
    String actionLabel = 'Fix';
    VoidCallback onAction = () {};

    if (location.state == LocationPermissionState.serviceDisabled) {
      title = 'GPS Location Services are Disabled';
      actionLabel = 'Enable GPS';
      onAction = () => _locationService.openLocationSettings();
    } else if (location.state == LocationPermissionState.permanentlyDenied) {
      title = 'Location Permission Permanently Denied';
      actionLabel = 'App Settings';
      onAction = () => _locationService.openAppSettings();
    } else if (location.state == LocationPermissionState.denied) {
      title = 'Location Permission Denied';
      actionLabel = 'Grant Access';
      onAction = () => Provider.of<PoliceProvider>(context, listen: false).updateLocation();
    } else {
      title = 'GPS Fix Unavailable';
      actionLabel = 'Retry';
      onAction = () => Provider.of<PoliceProvider>(context, listen: false).updateLocation();
    }

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
          const Icon(Icons.location_off, color: Color(0xFFFBBF24), size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              location.errorMessage ?? title,
              style: const TextStyle(color: Color(0xFFFEF3C7), fontSize: 12),
            ),
          ),
          const SizedBox(width: 8),
          ElevatedButton(
            onPressed: onAction,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFF59E0B),
              foregroundColor: Colors.black,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              textStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
            child: Text(actionLabel),
          ),
        ],
      ),
    );
  }

  Widget _buildAlertBanner({
    required String message,
    required bool isError,
    required VoidCallback onDismiss,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isError ? const Color(0xFF881337) : const Color(0xFF064E3B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isError ? const Color(0xFFF43F5E) : const Color(0xFF10B981),
        ),
      ),
      child: Row(
        children: [
          Icon(
            isError ? Icons.error_outline : Icons.check_circle_outline,
            color: isError ? const Color(0xFFFECDD3) : const Color(0xFFA7F3D0),
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: isError ? const Color(0xFFFECDD3) : const Color(0xFFA7F3D0),
                fontSize: 12,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16, color: Colors.white70),
            onPressed: onDismiss,
          ),
        ],
      ),
    );
  }

  Widget _buildAssignmentCard(
    PoliceProvider policeProvider,
    PatrolAssignmentModel? assignment,
  ) {
    if (assignment == null) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF334155)),
        ),
        child: const Column(
          children: [
            Icon(Icons.radio_button_checked, size: 48, color: Color(0xFF64748B)),
            SizedBox(height: 12),
            Text(
              'No Active Patrol Assignment',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
            SizedBox(height: 6),
            Text(
              'You are in standby mode. Standby for command center dispatch or pull down to refresh.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
            ),
          ],
        ),
      );
    }

    Color statusColor;
    switch (assignment.status) {
      case 'ASSIGNED':
        statusColor = const Color(0xFFF59E0B);
        break;
      case 'ACKNOWLEDGED':
        statusColor = const Color(0xFF3B82F6);
        break;
      case 'ARRIVED':
        statusColor = const Color(0xFF10B981);
        break;
      case 'COMPLETED':
        statusColor = const Color(0xFF64748B);
        break;
      default:
        statusColor = const Color(0xFF06B6D4);
    }

    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: statusColor.withValues(alpha: 0.5)),
        boxShadow: [
          BoxShadow(
            color: statusColor.withValues(alpha: 0.1),
            blurRadius: 12,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Status Badge & ID
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: statusColor),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        color: statusColor,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      assignment.status,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                'Deployment #${assignment.id}',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF94A3B8),
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // PRP Target Details
          Text(
            'Target: Patrol Priority Point #${assignment.prpId}',
            style: const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),

          if (assignment.prp != null) ...[
            const SizedBox(height: 4),
            Text(
              'Coordinates: ${assignment.prp!.latitude.toStringAsFixed(4)}, ${assignment.prp!.longitude.toStringAsFixed(4)} • Coverage: ${assignment.prp!.coverageRadiusMeters}m',
              style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
            ),
          ],

          const SizedBox(height: 12),

          // Routing Metrics
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFF0F172A),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                Column(
                  children: [
                    const Text('Distance',
                        style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                    const SizedBox(height: 2),
                    Text(
                      assignment.distanceMeters != null
                          ? '${(assignment.distanceMeters! / 1000).toStringAsFixed(2)} km'
                          : 'Calculating...',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF38BDF8),
                      ),
                    ),
                  ],
                ),
                Container(height: 24, width: 1, color: const Color(0xFF334155)),
                Column(
                  children: [
                    const Text('Est. Duration',
                        style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                    const SizedBox(height: 2),
                    Text(
                      assignment.estimatedDurationSeconds != null
                          ? '${(assignment.estimatedDurationSeconds! / 60).round()} min'
                          : 'Calculating...',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF38BDF8),
                      ),
                    ),
                  ],
                ),
                Container(height: 24, width: 1, color: const Color(0xFF334155)),
                Column(
                  children: [
                    const Text('Shift',
                        style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
                    const SizedBox(height: 2),
                    Text(
                      assignment.prp?.shiftType ?? 'NIGHT',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF34D399),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // Lifecycle Action Buttons
          if (assignment.isAssigned)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.navigation_outlined),
                label: policeProvider.isActionInProgress
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Acknowledge & Start Travel (En Route)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF2563EB),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: policeProvider.isActionInProgress
                    ? null
                    : () => policeProvider.acknowledgeAssignment(assignment.id),
              ),
            )
          else if (assignment.isAcknowledged)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.location_on_outlined),
                label: policeProvider.isActionInProgress
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Mark Arrived On-Scene (AT PRP)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF059669),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: policeProvider.isActionInProgress
                    ? null
                    : () => policeProvider.markArrivedAtPRP(assignment.id),
              ),
            )
          else if (assignment.isArrived)
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.check_circle_outline),
                label: policeProvider.isActionInProgress
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : const Text('Complete Deployment (Release Unit)'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF475569),
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: policeProvider.isActionInProgress
                    ? null
                    : () => policeProvider.completeAssignment(assignment.id),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMapSection(
    LatLng mapCenter,
    LatLng? officerLatLng,
    LatLng? prpLatLng,
    PatrolAssignmentModel? assignment,
  ) {
    return Container(
      height: 260,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: mapCenter,
              initialZoom: 13.5,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.safezone.safezone_app',
              ),
              if (prpLatLng != null && assignment?.prp != null)
                CircleLayer(
                  circles: [
                    CircleMarker(
                      point: prpLatLng,
                      radius: assignment!.prp!.coverageRadiusMeters.toDouble(),
                      useRadiusInMeter: true,
                      color: const Color(0xFF06B6D4).withValues(alpha: 0.2),
                      borderColor: const Color(0xFF06B6D4),
                      borderStrokeWidth: 2,
                    ),
                  ],
                ),
              MarkerLayer(
                markers: [
                  if (officerLatLng != null)
                    Marker(
                      point: officerLatLng,
                      width: 36,
                      height: 36,
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF1D4ED8),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                          boxShadow: const [
                            BoxShadow(color: Colors.black45, blurRadius: 6),
                          ],
                        ),
                        child: const Icon(Icons.directions_car, color: Colors.white, size: 20),
                      ),
                    ),
                  if (prpLatLng != null)
                    Marker(
                      point: prpLatLng,
                      width: 36,
                      height: 36,
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF0891B2),
                          shape: BoxShape.circle,
                          border: Border.all(color: Colors.white, width: 2),
                          boxShadow: const [
                            BoxShadow(color: Colors.black45, blurRadius: 6),
                          ],
                        ),
                        child: const Icon(Icons.flag, color: Colors.white, size: 20),
                      ),
                    ),
                ],
              ),
            ],
          ),
          Positioned(
            right: 12,
            bottom: 12,
            child: FloatingActionButton.small(
              backgroundColor: const Color(0xFF1E293B),
              foregroundColor: Colors.white,
              onPressed: () => _recenterMap(mapCenter),
              child: const Icon(Icons.my_location),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSOSPlaceholderCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF881337)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(
              color: Color(0xFF881337),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.emergency_outlined, color: Color(0xFFFDA4AF), size: 24),
          ),
          const SizedBox(width: 14),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Emergency SOS Dispatch Channel',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFFFDA4AF),
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  'Channel Active • Automatic override on high-priority citizen alerts.',
                  style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
