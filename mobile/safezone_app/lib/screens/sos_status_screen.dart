import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/citizen_provider.dart';

class SOSStatusScreen extends StatelessWidget {
  const SOSStatusScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final citizenProvider = Provider.of<CitizenProvider>(context);
    final location = citizenProvider.currentLocation;
    final contacts = citizenProvider.emergencyContacts;

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
                  width: 110,
                  height: 110,
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
                      size: 60,
                      color: Colors.white,
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 20),

              const Text(
                'Distress Broadcast in Progress',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Status: ${citizenProvider.sosStatus}',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFFFDA4AF),
                ),
              ),

              const SizedBox(height: 24),

              // 2. Geolocation Telemetry Card
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

              // 3. Emergency Contacts Notified List
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

              // 4. Cancel / False Alarm Disarm Button
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
                onPressed: () {
                  citizenProvider.cancelSOS();
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}
