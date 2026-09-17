# SafeZone

> **AI-Assisted Intelligent Police Patrol Deployment and Emergency Response System**

SafeZone is an intelligent dispatch, risk-scoring, and dynamic patrol optimization platform designed to improve response times and maximize weighted crime-risk coverage for urban police operations and citizen emergency response.

---

## Architecture Overview

SafeZone consists of three integrated interfaces:
1. **Citizen Mobile App**: SOS dispatch, status monitoring, verified Safe Help Points.
2. **Police Mobile App**: Real-time deployment, PRP assignment management, SOS dispatch alerts and resolution workflow.
3. **Admin Dashboard**: Web-based tactical control center for crime management, PRP optimization, patrol unit dispatching, and quantitative evaluation.

### Core Processing Flow
```text
Historical Crime Data
  └──> Explainable Risk Scoring (Frequency, Severity, Recency, Time)
        └──> Candidate Patrol Locations
              └──> Dynamic PRP Optimization (Max-Cover constrained by patrol count)
                    └──> Patrol Assignment (Distance & availability)
                          └──> Emergency Response (SOS lifecycle management)
```

---

## Frozen Technology Stack

- **Mobile Application**: Flutter (Dart) with `flutter_map` / OpenStreetMap (Single unified application with Citizen & Police modules).
- **Admin Dashboard**: React + Vite with Leaflet / React Leaflet / OpenStreetMap.
- **Backend API**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic.
- **Database**: PostgreSQL with PostGIS extension.
- **Optimization & Analytics**: Python (NumPy, Pandas, Google OR-Tools).
- **Routing**: OSRM-compatible routing abstraction.
- **Authentication**: JWT with role-based authorization (ADMIN, POLICE, CITIZEN).
- **Push Notifications**: Firebase Cloud Messaging (FCM) abstraction.
- **Realtime**: REST APIs for operational workflows; WebSockets for active SOS tracking and live responder updates.

---

## Current Implementation Stage

- **Stage 1: Repository Foundation** (Completed)
  - FastAPI backend foundation with settings, logging, session setup, and `/health` endpoint.
  - React + Vite Admin Dashboard application shell.
  - Flutter Mobile App baseline configuration.
  - Environment specification (`.env.example`) and `.gitignore`.

---

## Local Development Setup

### 1. Environment Configuration
Copy the example environment configuration:
```bash
cp .env.example .env
```

### 2. Backend (FastAPI)
```bash
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Health Check: `http://localhost:8000/health`
- Interactive API Docs: `http://localhost:8000/docs`

Run tests:
```bash
python -m pytest
```

### 3. Admin Dashboard (React + Vite)
```bash
cd admin-dashboard
npm install
npm run dev
```
- Access at `http://localhost:5173`

Production build:
```bash
npm run build
```

### 4. Mobile Application (Flutter)
```bash
cd mobile/safezone_app
flutter pub get
flutter analyze
flutter test
```
