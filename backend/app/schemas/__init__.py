from app.schemas.auth import (
    CitizenRegisterRequest,
    TokenResponse,
    UserLoginRequest,
    UserResponse,
)
from app.schemas.crime import (
    CSVImportSummaryResponse,
    CSVRowError,
    CrimeIncidentCreateRequest,
    CrimeIncidentResponse,
    CrimeIncidentUpdateRequest,
    PaginatedCrimesResponse,
)
from app.schemas.help_point import (
    HelpPointCSVImportSummary,
    HelpPointCSVRowError,
    PaginatedHelpPointsResponse,
    SafeHelpPointCreateRequest,
    SafeHelpPointResponse,
    SafeHelpPointUpdateRequest,
)
from app.schemas.patrol import (
    OperationalStatusSummary,
    PaginatedPatrolUnitsResponse,
    PaginatedPoliceOfficersResponse,
    PatrolUnitCreateRequest,
    PatrolUnitResponse,
    PatrolUnitStatusUpdateRequest,
    PatrolUnitUpdateRequest,
    PoliceOfficerCreateRequest,
    PoliceOfficerResponse,
    PoliceOfficerUpdateRequest,
)
from app.schemas.prp_candidate import (
    CandidateGenerationConfigSchema,
    CandidateGenerationRequest,
    CandidatePRPResponse,
    PredefinedLocationSchema,
)
from app.schemas.risk import (
    LocationRiskRequest,
    RiskScoreBreakdownResponse,
    RiskScoreRecordRead,
    RiskWeightConfigSchema,
)

__all__ = [
    # Auth
    "CitizenRegisterRequest",
    "UserLoginRequest",
    "UserResponse",
    "TokenResponse",
    # Patrol
    "PoliceOfficerCreateRequest",
    "PoliceOfficerUpdateRequest",
    "PoliceOfficerResponse",
    "PaginatedPoliceOfficersResponse",
    "PatrolUnitCreateRequest",
    "PatrolUnitUpdateRequest",
    "PatrolUnitStatusUpdateRequest",
    "PatrolUnitResponse",
    "PaginatedPatrolUnitsResponse",
    "OperationalStatusSummary",
    # Crime
    "CrimeIncidentCreateRequest",
    "CrimeIncidentUpdateRequest",
    "CrimeIncidentResponse",
    "PaginatedCrimesResponse",
    "CSVRowError",
    "CSVImportSummaryResponse",
    # Help Points
    "SafeHelpPointCreateRequest",
    "SafeHelpPointUpdateRequest",
    "SafeHelpPointResponse",
    "PaginatedHelpPointsResponse",
    "HelpPointCSVRowError",
    "HelpPointCSVImportSummary",
    # Risk
    "RiskWeightConfigSchema",
    "LocationRiskRequest",
    "RiskScoreBreakdownResponse",
    "RiskScoreRecordRead",
    # PRP Candidate
    "PredefinedLocationSchema",
    "CandidateGenerationConfigSchema",
    "CandidatePRPResponse",
    "CandidateGenerationRequest",
]
