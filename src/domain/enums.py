from enum import Enum

class EmailStatus(str, Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    QUEUED_SEND = "QUEUED_SEND"    # Aprobado por el Juez (listo para envío directo)
    QUEUED_DRAFT = "QUEUED_DRAFT"  # Reprobado o modo borrador (requiere revisión)
    SENT = "SENT"
    DRAFTED = "DRAFTED"
    FAILED = "FAILED"