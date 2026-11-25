from enum import StrEnum


class DataOrigin(StrEnum):
    DEMO = "DEMO"
    LIVE = "LIVE"


class IntegrationState(StrEnum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
