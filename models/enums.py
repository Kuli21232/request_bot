import enum


class RequestStatus(str, enum.Enum):
    new = "new"
    open = "open"
    in_progress = "in_progress"
    waiting_for_user = "waiting_for_user"
    resolved = "resolved"
    closed = "closed"
    duplicate = "duplicate"


class RequestPriority(str, enum.Enum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class UserRole(str, enum.Enum):
    user = "user"
    agent = "agent"
    supervisor = "supervisor"
    admin = "admin"
