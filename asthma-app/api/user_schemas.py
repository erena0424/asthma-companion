"""Shared user profile schemas — matches frontend setup wizard PATCH body."""

from __future__ import annotations

from datetime import date as Date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class EmergencyContact(BaseModel):
    """Matches frontend ContactCard / ContactModal shape (camelCase keys)."""

    id: Optional[str] = None
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    model_config = {"extra": "allow"}


class UserProfileFields(BaseModel):
    name: Optional[str] = None
    profile_image_url: Optional[str] = Field(
        default=None,
        max_length=2048,
        description="HTTPS URL for the profile image (e.g. Cloudinary secure_url)",
    )
    date_of_birth: Optional[Date] = None
    emergency_contact: Optional[str] = None
    emergency_contacts: List[EmergencyContact] = Field(default_factory=list)
    preferred_reminder: Optional[str] = None
    contact_method: Optional[str] = None
    preferred_environment: Optional[str] = None
    care_goal: Optional[str] = None
    accessibility_needs: Optional[str] = None
    trigger_preferences: List[str] = Field(default_factory=list)
    trigger_sensitivities: Dict[str, float] = Field(default_factory=dict)
    symptoms: List[str] = Field(default_factory=list)
    tracking: List[str] = Field(default_factory=list)


class UserProfile(UserProfileFields):
    id: str
    email: EmailStr

    model_config = {"from_attributes": True}


class UserProfileUpdate(UserProfileFields):
    """All fields optional for PATCH."""

    name: Optional[str] = None
    profile_image_url: Optional[str] = Field(default=None, max_length=2048)
    date_of_birth: Optional[Date] = None
    emergency_contact: Optional[str] = None
    emergency_contacts: Optional[List[EmergencyContact]] = None
    preferred_reminder: Optional[str] = None
    contact_method: Optional[str] = None
    preferred_environment: Optional[str] = None
    care_goal: Optional[str] = None
    accessibility_needs: Optional[str] = None
    trigger_preferences: Optional[List[str]] = None
    trigger_sensitivities: Optional[Dict[str, float]] = None
    symptoms: Optional[List[str]] = None
    tracking: Optional[List[str]] = None


def emergency_contacts_to_legacy_string(contacts: list[dict[str, Any]] | None) -> str | None:
    """Build a single-line summary for legacy emergency_contact consumers."""
    if not contacts:
        return None
    parts: list[str] = []
    for contact in contacts:
        name = " ".join(
            p
            for p in (
                contact.get("firstName"),
                contact.get("last_name") or contact.get("lastName"),
            )
            if p
        ).strip()
        phone = contact.get("phone")
        if name and phone:
            parts.append(f"{name} — {phone}")
        elif name:
            parts.append(name)
        elif phone:
            parts.append(str(phone))
    return "; ".join(parts) if parts else None
