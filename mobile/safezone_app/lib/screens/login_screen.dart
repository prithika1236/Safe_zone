import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _loginFormKey = GlobalKey<FormState>();
  final _registerFormKey = GlobalKey<FormState>();

  // Login controllers
  late final TextEditingController _loginEmailController;
  late final TextEditingController _loginPasswordController;

  // Register controllers
  late final TextEditingController _regNameController;
  late final TextEditingController _regEmailController;
  late final TextEditingController _regPasswordController;
  late final TextEditingController _regPhoneController;

  bool _obscureLoginPassword = true;
  bool _obscureRegPassword = true;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _loginEmailController = TextEditingController();
    _loginPasswordController = TextEditingController();
    _regNameController = TextEditingController();
    _regEmailController = TextEditingController();
    _regPasswordController = TextEditingController();
    _regPhoneController = TextEditingController();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _loginEmailController.dispose();
    _loginPasswordController.dispose();
    _regNameController.dispose();
    _regEmailController.dispose();
    _regPasswordController.dispose();
    _regPhoneController.dispose();
    super.dispose();
  }

  Future<void> _submitLogin() async {
    if (!_loginFormKey.currentState!.validate()) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    await authProvider.login(
      _loginEmailController.text.trim(),
      _loginPasswordController.text,
    );
  }

  Future<void> _submitRegister() async {
    if (!_registerFormKey.currentState!.validate()) return;

    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final success = await authProvider.register(
      fullName: _regNameController.text.trim(),
      email: _regEmailController.text.trim(),
      password: _regPasswordController.text,
      phoneNumber: _regPhoneController.text.trim(),
    );

    if (success) {
      _loginEmailController.text = _regEmailController.text.trim();
      _tabController.animateTo(0);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // App Brand Header
                  Container(
                    width: 72,
                    height: 72,
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E3A8A),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF3B82F6).withValues(alpha: 0.3),
                          blurRadius: 20,
                          spreadRadius: 2,
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Icon(
                        Icons.shield,
                        size: 38,
                        color: Colors.white,
                      ),
                    ),
                  ),

                  const Text(
                    'SafeZone Portal',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'AI-Assisted Police Patrol & Citizen Safety Terminal',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFF94A3B8),
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Tab switcher: Sign In vs Citizen Sign Up
                  Container(
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: TabBar(
                      controller: _tabController,
                      indicatorColor: const Color(0xFF3B82F6),
                      indicatorSize: TabBarIndicatorSize.tab,
                      labelColor: Colors.white,
                      unselectedLabelColor: const Color(0xFF94A3B8),
                      labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                      tabs: const [
                        Tab(text: 'Sign In'),
                        Tab(text: 'Citizen Sign Up'),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Feedback Messages
                  if (authProvider.errorMessage != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF881337),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFF43F5E)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline, color: Color(0xFFFECDD3), size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              authProvider.errorMessage!,
                              style: const TextStyle(color: Color(0xFFFECDD3), fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),

                  if (authProvider.successMessage != null)
                    Container(
                      padding: const EdgeInsets.all(12),
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF064E3B),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF10B981)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.check_circle_outline, color: Color(0xFFA7F3D0), size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              authProvider.successMessage!,
                              style: const TextStyle(color: Color(0xFFA7F3D0), fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),

                  // Tab View Bodies
                  SizedBox(
                    height: 340,
                    child: TabBarView(
                      controller: _tabController,
                      children: [
                        // Tab 1: Sign In Form
                        Form(
                          key: _loginFormKey,
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              TextFormField(
                                controller: _loginEmailController,
                                keyboardType: TextInputType.emailAddress,
                                style: const TextStyle(color: Colors.white),
                                decoration: InputDecoration(
                                  labelText: 'Email Address',
                                  labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                  prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF64748B)),
                                  filled: true,
                                  fillColor: const Color(0xFF1E293B),
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                validator: (val) => val == null || !val.contains('@') ? 'Enter a valid email' : null,
                              ),
                              const SizedBox(height: 14),
                              TextFormField(
                                controller: _loginPasswordController,
                                obscureText: _obscureLoginPassword,
                                style: const TextStyle(color: Colors.white),
                                decoration: InputDecoration(
                                  labelText: 'Password',
                                  labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                  prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF64748B)),
                                  suffixIcon: IconButton(
                                    icon: Icon(_obscureLoginPassword ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: const Color(0xFF64748B)),
                                    onPressed: () => setState(() => _obscureLoginPassword = !_obscureLoginPassword),
                                  ),
                                  filled: true,
                                  fillColor: const Color(0xFF1E293B),
                                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                validator: (val) => val == null || val.length < 6 ? 'Password too short' : null,
                              ),
                              const SizedBox(height: 20),
                              ElevatedButton(
                                onPressed: authProvider.isLoading ? null : _submitLogin,
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: const Color(0xFF2563EB),
                                  foregroundColor: Colors.white,
                                  padding: const EdgeInsets.symmetric(vertical: 14),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                ),
                                child: authProvider.isLoading
                                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                    : const Text('Sign In', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold)),
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'Supports Police Officers, Administrators, and Citizens',
                                textAlign: TextAlign.center,
                                style: TextStyle(fontSize: 11, color: Color(0xFF64748B)),
                              ),
                            ],
                          ),
                        ),

                        // Tab 2: Citizen Register Form
                        Form(
                          key: _registerFormKey,
                          child: SingleChildScrollView(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                TextFormField(
                                  controller: _regNameController,
                                  style: const TextStyle(color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Full Name',
                                    labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                    prefixIcon: const Icon(Icons.person_outline, color: Color(0xFF64748B)),
                                    filled: true,
                                    fillColor: const Color(0xFF1E293B),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                  validator: (val) => val == null || val.trim().isEmpty ? 'Enter your name' : null,
                                ),
                                const SizedBox(height: 10),
                                TextFormField(
                                  controller: _regEmailController,
                                  keyboardType: TextInputType.emailAddress,
                                  style: const TextStyle(color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Email Address',
                                    labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                    prefixIcon: const Icon(Icons.email_outlined, color: Color(0xFF64748B)),
                                    filled: true,
                                    fillColor: const Color(0xFF1E293B),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                  validator: (val) => val == null || !val.contains('@') ? 'Enter a valid email' : null,
                                ),
                                const SizedBox(height: 10),
                                TextFormField(
                                  controller: _regPasswordController,
                                  obscureText: _obscureRegPassword,
                                  style: const TextStyle(color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Password (min 6 chars)',
                                    labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                    prefixIcon: const Icon(Icons.lock_outline, color: Color(0xFF64748B)),
                                    suffixIcon: IconButton(
                                      icon: Icon(_obscureRegPassword ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: const Color(0xFF64748B)),
                                      onPressed: () => setState(() => _obscureRegPassword = !_obscureRegPassword),
                                    ),
                                    filled: true,
                                    fillColor: const Color(0xFF1E293B),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                  validator: (val) => val == null || val.length < 6 ? 'Password must be >= 6 chars' : null,
                                ),
                                const SizedBox(height: 10),
                                TextFormField(
                                  controller: _regPhoneController,
                                  keyboardType: TextInputType.phone,
                                  style: const TextStyle(color: Colors.white),
                                  decoration: InputDecoration(
                                    labelText: 'Phone Number (Optional)',
                                    labelStyle: const TextStyle(color: Color(0xFF94A3B8)),
                                    prefixIcon: const Icon(Icons.phone_outlined, color: Color(0xFF64748B)),
                                    filled: true,
                                    fillColor: const Color(0xFF1E293B),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                ),
                                const SizedBox(height: 14),
                                ElevatedButton(
                                  onPressed: authProvider.isLoading ? null : _submitRegister,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF059669),
                                    foregroundColor: Colors.white,
                                    padding: const EdgeInsets.symmetric(vertical: 12),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                  ),
                                  child: authProvider.isLoading
                                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                      : const Text('Create Citizen Account', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
