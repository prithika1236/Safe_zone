import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/citizen_provider.dart';

class SOSStatusScreen extends StatefulWidget {
  const SOSStatusScreen({super.key});

  @override
  State<SOSStatusScreen> createState() => _SOSStatusScreenState();
}

class _SOSStatusScreenState extends State<SOSStatusScreen> {
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    // Poll active SOS status every 3 seconds while emergency screen is open
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) {
      if (mounted) {
        Provider.of<CitizenProvider>(context, listen: false).fetchActiveSOS();
      }
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final citizenProvider = Provider.of<CitizenProvider>(context);
    final location = citizenProvider.currentLocation;
    final contacts = citizenProvider.emergencyContacts;
    final activeSOS = citizenProvider.activeSOS;

    String statusDisplay = citizenProvider.sosStatus;
    Color statusBadgeColor = const Color(0xFFE11D48);

    if (activeSOS != null) {
      switch (activeSOS.status) {
        case 'PENDING':
          statusDisplay = 'Awaiting Patrol Assignment...';
          statusBadgeColor = const Color(0xFFF59E0B);
          break;
        case 'ASSIGNED':
          statusDisplay = 'Patrol Dispatched';
          statusBadgeColor = const Color(0xFF3B82F6);
          break;
        case 'ACCEPTED':
          statusDisplay = 'Patrol Responding';
          statusBadgeColor = const Color(0xFF2563EB);
          break;
        case 'EN_ROUTE':
          statusDisplay = 'Patrol EN ROUTE to your location';
          statusBadgeColor = const Color(0xFF8B5CF6);
          break;
        case 'ARRIVED':
          statusDisplay = 'Patrol ARRIVED on-scene';
          statusBadgeColor = const Color(0xFF10B981);
          break;
        case 'RESOLVED':
          statusDisplay = 'Emergency RESOLVED';
          statusBadgeColor = const Color(0xFF059669);
          break;
        case 'CANCELLED':
          statusDisplay = 'Emergency CANCELLED';
          statusBadgeColor = const Color(0xFF64748B);
          break;
      }
    }

    return Scaffold(
      backgroundColor: const Color(0xFF4C0519), // Deep emergency crimson
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.warning_amber_rounded, color: Color(0xFFFDA4AF)),
            SizedBox(width: 8),
            Text(
              'EMERGENCY SOS ACTIVE',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                letterSpacing: 1.0,
                color: Color(0xFFFDA4AF),
                fontSize: 16,
              ),
            ),
          ],
        ),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. Pulsing Distress Beacon Header
              Center(
                child: Container(
                  width: 100,
                  height: 100,
                  decoration: BoxDecoration(
                    color: const Color(0xFFE11D48),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFFF43F5E).withValues(alpha: 0.5),
                        blurRadius: 30,
                        spreadRadius: 8,
                      ),
                    ],
                  ),
                  child: const Center(
                    child: Icon(
                      Icons.emergency,
                      size: 54,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 18),

              const Text(
                'Distress Broadcast Active',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 6),
              Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusBadgeColor.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: statusBadgeColor),
                  ),
                  child: Text(
                    statusDisplay,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                      color: statusBadgeColor == const Color(0xFF64748B)
                          ? const Color(0xFFCBD5E1)
                          : const Color(0xFFFDA4AF),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 20),

              // 2. Dispatch / Responder Status Card
              if (activeSOS != null && activeSOS.patrolAssigned)
                Container(
                  margin: const EdgeInsets.only(bottom: 16),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B).withValues(alpha: 0.95),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF38BDF8)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.shield_outlined, color: Color(0xFF38BDF8), size: 20),
                          SizedBox(width: 8),
                          Text(
                            'Assigned Police Patrol Unit',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Call Sign: ${activeSOS.patrolCallSign ?? "PATROL UNIT"}',
                        style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold, fontSize: 14),
                      ),
                      if (activeSOS.distanceMeters != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(
                            'Distance: ${(activeSOS.distanceMeters! / 1000).toStringAsFixed(2)} km  •  ETA: ${activeSOS.estimatedDurationSeconds != null ? (activeSOS.estimatedDurationSeconds! / 60).toStringAsFixed(0) : "N/A"} mins',
                            style: const TextStyle(color: Color(0xFFE2E8F0), fontSize: 12),
                          ),
                        ),
                    ],
                  ),
                ),

              // 3. Geolocation Telemetry Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFF43F5E)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.my_location, color: Color(0xFFF43F5E), size: 18),
                        SizedBox(width: 8),
                        Text(
                          'Live Coordinates Telemetry',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                            fontSize: 13,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (location?.isSuccess == true) ...[
                      Text(
                        'Latitude: ${location!.latitude!.toStringAsFixed(6)}',
                        style: const TextStyle(color: Color(0xFFE2E8F0), fontFamily: 'monospace', fontSize: 13),
                      ),
                      Text(
                        'Longitude: ${location.longitude!.toStringAsFixed(6)}',
                        style: const TextStyle(color: Color(0xFFE2E8F0), fontFamily: 'monospace', fontSize: 13),
                      ),
                    ] else ...[
                      const Text(
                        'Acquiring High-Precision GPS Fix...',
                        style: TextStyle(color: Color(0xFFFBBF24), fontSize: 13),
                      ),
                    ],
                    if (citizenProvider.sosTriggeredAt != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8),
                        child: Text(
                          'Triggered at: ${citizenProvider.sosTriggeredAt!.toLocal().toString().split(".")[0]}',
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ),
                  ],
                ),
              ),

              const SizedBox(height: 16),

              // 4. Emergency Contacts Notified List
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B).withValues(alpha: 0.9),
                  borderRadius: BorderRadius.circular(12),
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
                            Icon(Icons.contacts, color: Color(0xFF38BDF8), size: 18),
                            SizedBox(width: 8),
                            Text(
                              'Emergency Contacts',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: Colors.white,
                                fontSize: 13,
                              ),
                            ),
                          ],
                        ),
                        Text(
                          '${contacts.length} Configured',
                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    if (contacts.isEmpty)
                      const Text(
                        'No emergency contacts configured. Add contacts in home screen.',
                        style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                      )
                    else
                      ...contacts.map(
                        (c) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                '${c.name} (${c.relationship})',
                                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600),
                              ),
                              Text(
                                c.phoneNumber,
                                style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontFamily: 'monospace'),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              const SizedBox(height: 24),

              // 5. Cancel / False Alarm Disarm Button
              ElevatedButton.icon(
                icon: const Icon(Icons.cancel_outlined),
                label: const Text(
                  'Cancel Emergency (False Alarm)',
                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1E293B),
                  foregroundColor: Colors.white,
                  side: const BorderSide(color: Color(0xFF64748B)),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                onPressed: () async {
                  await citizenProvider.cancelSOS();
                  if (context.mounted) {
                    Navigator.of(context).pop();
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
