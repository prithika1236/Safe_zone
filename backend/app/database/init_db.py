from datetime import datetime, timezone
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database.session import AsyncSessionLocal, Base, engine
from app.models.crime import CrimeIncident
from app.models.enums import PatrolStatus, SafeHelpPointType, UserRole
from app.models.help_point import SafeHelpPoint
from app.models.patrol import PatrolUnit
from app.models.user import EmergencyContact, PoliceOfficer, User
from app.services.crime_service import create_point_geometry

logger = logging.getLogger("safezone.init_db")


async def init_database():
    """Create database tables and seed default presentation accounts and sample operational data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Check if Admin already exists
        admin_check = await db.execute(select(User).where(User.email == "admin@safezone.gov"))
        if admin_check.scalar_one_or_none() is None:
            logger.info("Seeding initial administrator user...")
            admin = User(
                email="admin@safezone.gov",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Chief Inspector Admin",
                phone_number="+91 9900011100",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)

        # 2. Check if Police Officer exists
        officer_user_check = await db.execute(select(User).where(User.email == "officer@police.gov"))
        if officer_user_check.scalar_one_or_none() is None:
            logger.info("Seeding initial police officer and patrol unit...")
            pol_user = User(
                email="officer@police.gov",
                hashed_password=hash_password("OfficerPass123!"),
                full_name="Officer Alex Turner",
                phone_number="+91 9888877777",
                role=UserRole.POLICE,
                is_active=True,
            )
            db.add(pol_user)
            await db.flush()

            officer = PoliceOfficer(
                user_id=pol_user.id,
                badge_number="BADGE-101",
                rank="SERGEANT",
                department="Central Metropolitan Patrol",
                is_on_duty=True,
            )
            db.add(officer)
            await db.flush()

            patrol = PatrolUnit(
                call_sign="PATROL-ALPHA",
                officer_id=officer.id,
                status=PatrolStatus.AVAILABLE,
                current_location=create_point_geometry(12.9720, 77.5950),
                is_active=True,
            )
            db.add(patrol)

        # 3. Check if Citizen user exists
        citizen_check = await db.execute(select(User).where(User.email == "citizen@example.com"))
        if citizen_check.scalar_one_or_none() is None:
            logger.info("Seeding initial citizen account...")
            citizen = User(
                email="citizen@example.com",
                hashed_password=hash_password("CitizenPass123!"),
                full_name="Jane Citizen",
                phone_number="+91 9123456789",
                role=UserRole.CITIZEN,
                is_active=True,
            )
            db.add(citizen)
            await db.flush()

            # Add sample emergency contacts
            ec1 = EmergencyContact(
                user_id=citizen.id,
                name="David Citizen",
                phone_number="+91 9876543210",
                relationship="Spouse",
                is_primary=True,
            )
            ec2 = EmergencyContact(
                user_id=citizen.id,
                name="Mary Citizen",
                phone_number="+91 9876543211",
                relationship="Parent",
                is_primary=False,
            )
            db.add_all([ec1, ec2])

        # 4. Seed sample Safe Help Points if none exist
        hp_check = await db.execute(select(SafeHelpPoint))
        if len(hp_check.scalars().all()) == 0:
            logger.info("Seeding sample Safe Help Points...")
            hps = [
                SafeHelpPoint(
                    name="MG Road Police Station",
                    category=SafeHelpPointType.POLICE_STATION,
                    location=create_point_geometry(12.9750, 77.6050),
                    address="12 MG Road, Central District",
                    contact_phone="080-22942555",
                    is_24_7=True,
                    is_verified=True,
                    is_active=True,
                ),
                SafeHelpPoint(
                    name="Victoria Hospital Emergency Trauma Center",
                    category=SafeHelpPointType.HOSPITAL,
                    location=create_point_geometry(12.9620, 77.5750),
                    address="Fort Road, City Market",
                    contact_phone="080-26701150",
                    is_24_7=True,
                    is_verified=True,
                    is_active=True,
                ),
                SafeHelpPoint(
                    name="Commercial Street 24/7 Pharmacy",
                    category=SafeHelpPointType.PHARMACY_24_7,
                    location=create_point_geometry(12.9815, 77.6090),
                    address="88 Commercial Street",
                    contact_phone="080-25588900",
                    is_24_7=True,
                    is_verified=True,
                    is_active=True,
                ),
                SafeHelpPoint(
                    name="Cubbon Park Metro Security Post",
                    category=SafeHelpPointType.TRANSIT_HUB,
                    location=create_point_geometry(12.9790, 77.5920),
                    address="Kasturba Road Entrance",
                    contact_phone="080-22960000",
                    is_24_7=True,
                    is_verified=True,
                    is_active=True,
                ),
            ]
            db.add_all(hps)

        # 5. Seed sample Crime Incidents if none exist
        crime_check = await db.execute(select(CrimeIncident))
        if len(crime_check.scalars().all()) == 0:
            logger.info("Seeding sample Crime Incidents for Risk Analysis...")
            crimes = [
                CrimeIncident(
                    incident_number="CR-2026-001",
                    category="Theft / Larceny",
                    severity=3,
                    incident_time=datetime.now(timezone.utc),
                    location=create_point_geometry(12.9716, 77.5946),
                    description="Mobile phone snatched near bus stop",
                    is_active=True,
                ),
                CrimeIncident(
                    incident_number="CR-2026-002",
                    category="Assault",
                    severity=4,
                    incident_time=datetime.now(timezone.utc),
                    location=create_point_geometry(12.9730, 77.5970),
                    description="Physical altercation reported at alleyway",
                    is_active=True,
                ),
                CrimeIncident(
                    incident_number="CR-2026-003",
                    category="Robbery",
                    severity=5,
                    incident_time=datetime.now(timezone.utc),
                    location=create_point_geometry(12.9690, 77.5910),
                    description="Armed robbery attempt near ATM kiosk",
                    is_active=True,
                ),
                CrimeIncident(
                    incident_number="CR-2026-004",
                    category="Harassment",
                    severity=2,
                    incident_time=datetime.now(timezone.utc),
                    location=create_point_geometry(12.9755, 77.6010),
                    description="Street harassment reported near market entrance",
                    is_active=True,
                ),
            ]
            db.add_all(crimes)

        await db.commit()
        logger.info("SafeZone database schema & initial seed data ready!")
