from enum import Enum

class EmailStatus(str, Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    SENT = "SENT"
    DRAFTED = "DRAFTED"
    FAILED = "FAILED"