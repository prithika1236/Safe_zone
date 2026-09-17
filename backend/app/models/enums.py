import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    POLICE = "POLICE"
    CITIZEN = "CITIZEN"


class PatrolStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    EN_ROUTE = "EN_ROUTE"
    ON_SCENE = "ON_SCENE"
    OFF_DUTY = "OFF_DUTY"


class PRPStatus(str, enum.Enum):
    RECOMMENDED = "RECOMMENDED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OptimizationRunStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SOSStatus(str, enum.Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class SafeHelpPointType(str, enum.Enum):
    POLICE_STATION = "POLICE_STATION"
    HOSPITAL = "HOSPITAL"
    SHELTER = "SHELTER"
    FIRE_STATION = "FIRE_STATION"
    HELP_DESK = "HELP_DESK"
    OTHER = "OTHER"
