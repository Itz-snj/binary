"""Audit event service.

Wraps db.create_audit_event / list_audit_events with helpers that
record common operator actions consistently (approval, bypass,
config change, preflight, webhook receipt).
"""
