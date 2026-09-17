"""Explicit local decisions about notification delivery."""

from enum import StrEnum


class AlertStatus(StrEnum):
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    UNKNOWN = "unknown"
    SUPPRESSED = "suppressed"


class AlertDecision(StrEnum):
    RECEIVED = "received"
    DISMISS = "dismiss"
    RETRY = "retry"


UNCERTAIN = {AlertStatus.UNKNOWN, AlertStatus.SENDING}
SYSTEM_TRANSITIONS = {
    AlertStatus.PENDING: {AlertStatus.SENDING, AlertStatus.SUPPRESSED},
    AlertStatus.SENDING: {AlertStatus.SENT, AlertStatus.UNKNOWN, AlertStatus.PENDING},
}


def resolved_status(current: str, decision: AlertDecision) -> AlertStatus:
    if current in UNCERTAIN:
        return {
            AlertDecision.RECEIVED: AlertStatus.SENT,
            AlertDecision.DISMISS: AlertStatus.SUPPRESSED,
            AlertDecision.RETRY: AlertStatus.PENDING,
        }[decision]
    if current == AlertStatus.PENDING and decision == AlertDecision.DISMISS:
        return AlertStatus.SUPPRESSED
    raise ValueError("Decision is not allowed for this alert state; inspect the alert again")
