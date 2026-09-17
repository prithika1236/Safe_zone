# SafeZone Database Architecture & Domain Models

This document specifies the PostgreSQL + PostGIS database schema, normalized entities, spatial columns, and relationships for SafeZone.

---

## 1. Domain Entities & Schemas

### 1.1 `users`
Core identity table supporting role-based access control.
- `id` (INTEGER, Primary Key, Autoincrement)
- `email` (VARCHAR(255), Unique, Indexed, NOT NULL)
- `hashed_password` (VARCHAR(255), NOT NULL)
- `full_name` (VARCHAR(255), NOT NULL)
- `role` (VARCHAR(32), Indexed, NOT NULL): `ADMIN`, `POLICE`, `CITIZEN`
- `phone_number` (VARCHAR(32), Nullable)
- `is_active` (BOOLEAN, Default `true`, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.2 `police_officers`
Operational extension for police personnel.
- `id` (INTEGER, Primary Key, Autoincrement)
- `user_id` (INTEGER, Foreign Key `users.id` ON DELETE CASCADE, Unique, Indexed, NOT NULL)
- `badge_number` (VARCHAR(64), Unique, Indexed, NOT NULL)
- `rank` (VARCHAR(64), Nullable)
- `department` (VARCHAR(128), Nullable)
- `is_on_duty` (BOOLEAN, Default `false`, NOT NULL)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.3 `patrol_units`
Tactical patrol units available for dispatch and PRP assignment.
- `id` (INTEGER, Primary Key, Autoincrement)
- `call_sign` (VARCHAR(64), Unique, Indexed, NOT NULL)
- `officer_id` (INTEGER, Foreign Key `police_officers.id` ON DELETE SET NULL, Nullable)
- `status` (VARCHAR(32), Indexed, NOT NULL): `AVAILABLE`, `BUSY`, `EN_ROUTE`, `ON_SCENE`, `OFF_DUTY`
- `current_location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, Nullable)
- `last_location_update` (TIMESTAMP WITH TIME ZONE, Nullable)
- `is_active` (BOOLEAN, Default `true`, NOT NULL)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.4 `crime_incidents`
Historical and reported crime incidents used for risk calculations and optimization.
- `id` (INTEGER, Primary Key, Autoincrement)
- `incident_number` (VARCHAR(64), Unique, Indexed, NOT NULL)
- `category` (VARCHAR(128), Indexed, NOT NULL)
- `severity` (INTEGER, Default `1`, NOT NULL): Range 1 (Low) to 5 (Critical)
- `incident_time` (TIMESTAMP WITH TIME ZONE, Indexed, NOT NULL)
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `description` (TEXT, Nullable)
- `is_active` (BOOLEAN, Default `true`, NOT NULL)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.5 `optimization_runs`
Audit and parameter record for dynamic Patrol Response Point (PRP) generation.
- `id` (INTEGER, Primary Key, Autoincrement)
- `run_time` (TIMESTAMP WITH TIME ZONE, Indexed, NOT NULL)
- `shift` (VARCHAR(64), NOT NULL)
- `available_patrol_count` (INTEGER, NOT NULL)
- `coverage_radius_km` (FLOAT, Default `3.0`, NOT NULL)
- `parameters` (JSON, Nullable)
- `metrics` (JSON, Nullable): Evaluation metrics (risk coverage %, distance)
- `status` (VARCHAR(32), Indexed, NOT NULL): `PENDING`, `APPROVED`, `REJECTED`
- `created_by_id` (INTEGER, Foreign Key `users.id` ON DELETE SET NULL, Nullable)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.6 `prp_locations`
Dynamically computed Patrol Response Points.
- `id` (INTEGER, Primary Key, Autoincrement)
- `optimization_run_id` (INTEGER, Foreign Key `optimization_runs.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `name` (VARCHAR(128), NOT NULL)
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `coverage_radius_km` (FLOAT, Default `3.0`, NOT NULL)
- `priority_score` (FLOAT, Default `0.0`, NOT NULL)
- `status` (VARCHAR(32), Indexed, NOT NULL): `RECOMMENDED`, `APPROVED`, `ACTIVE`, `COMPLETED`, `CANCELLED`
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.7 `patrol_assignments`
Deployment bindings linking patrol units to active PRPs.
- `id` (INTEGER, Primary Key, Autoincrement)
- `patrol_unit_id` (INTEGER, Foreign Key `patrol_units.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `prp_location_id` (INTEGER, Foreign Key `prp_locations.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `optimization_run_id` (INTEGER, Foreign Key `optimization_runs.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `shift` (VARCHAR(64), NOT NULL)
- `status` (VARCHAR(32), Indexed, NOT NULL): `ASSIGNED`, `ACKNOWLEDGED`, `ARRIVED`, `COMPLETED`, `CANCELLED`
- `assigned_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `acknowledged_at` (TIMESTAMP WITH TIME ZONE, Nullable)
- `arrived_at` (TIMESTAMP WITH TIME ZONE, Nullable)
- `completed_at` (TIMESTAMP WITH TIME ZONE, Nullable)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.8 `sos_requests`
Citizen emergency alert lifecycle records.
- `id` (INTEGER, Primary Key, Autoincrement)
- `citizen_id` (INTEGER, Foreign Key `users.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `status` (VARCHAR(32), Indexed, NOT NULL): `PENDING`, `ASSIGNED`, `ACCEPTED`, `EN_ROUTE`, `ARRIVED`, `RESOLVED`, `CANCELLED`
- `assigned_patrol_unit_id` (INTEGER, Foreign Key `patrol_units.id` ON DELETE SET NULL, Indexed, Nullable)
- `trigger_time` (TIMESTAMP WITH TIME ZONE, Indexed, NOT NULL)
- `accepted_time` (TIMESTAMP WITH TIME ZONE, Nullable)
- `en_route_time` (TIMESTAMP WITH TIME ZONE, Nullable)
- `arrived_time` (TIMESTAMP WITH TIME ZONE, Nullable)
- `resolved_time` (TIMESTAMP WITH TIME ZONE, Nullable)
- `notes` (TEXT, Nullable)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.9 `location_updates`
Telemetry time-series for responder position tracking.
- `id` (INTEGER, Primary Key, Autoincrement)
- `patrol_unit_id` (INTEGER, Foreign Key `patrol_units.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `speed` (FLOAT, Nullable)
- `heading` (FLOAT, Nullable)
- `battery_level` (FLOAT, Nullable)
- `recorded_at` (TIMESTAMP WITH TIME ZONE, Indexed, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.10 `emergency_contacts`
Citizen emergency notification recipients.
- `id` (INTEGER, Primary Key, Autoincrement)
- `user_id` (INTEGER, Foreign Key `users.id` ON DELETE CASCADE, Indexed, NOT NULL)
- `name` (VARCHAR(255), NOT NULL)
- `phone_number` (VARCHAR(32), NOT NULL)
- `relationship_type` (VARCHAR(64), Nullable)
- `is_active` (BOOLEAN, Default `true`, NOT NULL)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

### 1.11 `risk_scores`
Explainable spatial risk values aggregated across frequency, severity, recency, and time-of-day.
- `id` (INTEGER, Primary Key, Autoincrement)
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `grid_identifier` (VARCHAR(64), Indexed, Nullable)
- `frequency_score` (FLOAT, NOT NULL)
- `severity_score` (FLOAT, NOT NULL)
- `recency_score` (FLOAT, NOT NULL)
- `time_score` (FLOAT, NOT NULL)
- `total_risk_score` (FLOAT, Indexed, NOT NULL)
- `calculated_at` (TIMESTAMP WITH TIME ZONE, Indexed, NOT NULL)

### 1.12 `safe_help_points`
Public safety and assistance facilities (hospitals, police stations, shelters).
- `id` (INTEGER, Primary Key, Autoincrement)
- `name` (VARCHAR(255), Indexed, NOT NULL)
- `category` (VARCHAR(32), Indexed, NOT NULL): `POLICE_STATION`, `HOSPITAL`, `SHELTER`, `FIRE_STATION`, `HELP_DESK`, `OTHER`
- `location` (GEOGRAPHY(POINT, 4326), PostGIS GiST Indexed, NOT NULL)
- `address` (VARCHAR(512), Nullable)
- `contact_number` (VARCHAR(32), Nullable)
- `is_verified` (BOOLEAN, Default `false`, Indexed, NOT NULL)
- `is_active` (BOOLEAN, Default `true`, Indexed, NOT NULL)
- `created_at`, `updated_at` (TIMESTAMP WITH TIME ZONE, NOT NULL)

---

## 2. Spatial Indexing & SRID Standards

- **SRID Standard**: WGS 84 (EPSG:4326) using PostGIS `GEOGRAPHY(POINT, 4326)` for geodesic accuracy on spherical coordinate calculations (meters/kilometers without map projection distortion).
- **Index Type**: GiST (Generalized Search Tree) spatial indexing is automatically configured for all `location` and `current_location` spatial columns.
- **Distance Calculation**: Spatial queries leverage `ST_DWithin` and `ST_Distance` on geography types.
