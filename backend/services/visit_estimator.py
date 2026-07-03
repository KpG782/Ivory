from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


CURRENT_YEAR = datetime.now(UTC).year

ESTIMATE_DISCLAIMER = "Educational estimate — not a diagnosis or a final price."

_EMAIL_RE = r"[^@\s]+@[^@\s]+\.[^@\s]+"


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    field: str | None = None
    message: str | None = None


def validate_visit_inputs(service_type: str, data: dict[str, Any]) -> ValidationResult:
    validators = {
        "cleaning": _validate_cleaning,
        "emergency": _validate_emergency,
        "cosmetic": _validate_cosmetic,
    }
    validator = validators.get(service_type)
    if validator is None:
        return ValidationResult(False, None, "Unsupported service type.")
    return validator(data)


def estimate_visit(service_type: str, data: dict[str, Any]) -> dict[str, Any]:
    estimators = {
        "cleaning": _estimate_cleaning,
        "emergency": _estimate_emergency,
        "cosmetic": _estimate_cosmetic,
    }
    estimator = estimators.get(service_type)
    if estimator is None:
        raise ValueError(f"Unsupported service type: {service_type}")
    return estimator(data)


def _validate_cleaning(data: dict[str, Any]) -> ValidationResult:
    name_result = _validate_patient_name(data)
    if name_result is not None:
        return name_result

    email_result = _validate_contact_email(data)
    if email_result is not None:
        return email_result

    last_visit_year = int(data["last_visit_year"])
    if last_visit_year <= 1900 or last_visit_year > CURRENT_YEAR:
        return ValidationResult(
            False,
            "last_visit_year",
            f"Last dental visit year must be between 1901 and {CURRENT_YEAR}.",
        )

    status_result = _validate_insurance_status(data)
    if status_result is not None:
        return status_result

    preferred_time = str(data["preferred_time"]).lower()
    if preferred_time not in {"morning", "afternoon", "evening"}:
        return ValidationResult(False, "preferred_time", "Preferred time must be morning, afternoon, or evening.")

    return ValidationResult(True)


def _validate_emergency(data: dict[str, Any]) -> ValidationResult:
    name_result = _validate_patient_name(data)
    if name_result is not None:
        return name_result

    contact_phone = str(data["contact_phone"])
    if len(re.sub(r"\D", "", contact_phone)) < 7:
        return ValidationResult(False, "contact_phone", "Contact phone must contain at least 7 digits.")

    issue_type = str(data["issue_type"]).lower()
    if issue_type not in {"toothache", "chipped_tooth", "swelling", "lost_filling"}:
        return ValidationResult(
            False,
            "issue_type",
            "Issue type must be toothache, chipped_tooth, swelling, or lost_filling.",
        )

    pain_level = int(data["pain_level"])
    if pain_level < 0 or pain_level > 10:
        return ValidationResult(False, "pain_level", "Please enter a pain level between 0 and 10.")

    status_result = _validate_insurance_status(data)
    if status_result is not None:
        return status_result

    return ValidationResult(True)


def _validate_cosmetic(data: dict[str, Any]) -> ValidationResult:
    name_result = _validate_patient_name(data)
    if name_result is not None:
        return name_result

    email_result = _validate_contact_email(data)
    if email_result is not None:
        return email_result

    treatment = str(data["treatment"]).lower()
    if treatment not in {"whitening", "veneers", "aligners", "bonding"}:
        return ValidationResult(False, "treatment", "Treatment must be whitening, veneers, aligners, or bonding.")

    budget_band = str(data["budget_band"]).lower()
    if budget_band not in {"basic", "standard", "premium"}:
        return ValidationResult(False, "budget_band", "Budget band must be basic, standard, or premium.")

    timeline = str(data["timeline"]).lower()
    if timeline not in {"asap", "this_month", "flexible"}:
        return ValidationResult(False, "timeline", "Timeline must be asap, this_month, or flexible.")

    return ValidationResult(True)


def _validate_patient_name(data: dict[str, Any]) -> ValidationResult | None:
    patient_name = str(data["patient_name"]).strip()
    alpha_tokens = [token for token in re.findall(r"[A-Za-z]+", patient_name)]
    if len(alpha_tokens) < 2:
        return ValidationResult(False, "patient_name", "Patient name must include a first and last name.")
    return None


def _validate_contact_email(data: dict[str, Any]) -> ValidationResult | None:
    contact_email = str(data["contact_email"]).strip()
    if not re.fullmatch(_EMAIL_RE, contact_email):
        return ValidationResult(False, "contact_email", "Contact email must be a valid address like maria@example.com.")
    return None


def _validate_insurance_status(data: dict[str, Any]) -> ValidationResult | None:
    insurance_status = str(data["insurance_status"]).lower()
    if insurance_status not in {"insured", "self_pay"}:
        return ValidationResult(False, "insurance_status", "Insurance status must be insured or self_pay.")
    return None


def _estimate_cleaning(data: dict[str, Any]) -> dict[str, Any]:
    base = 140.0
    last_visit_year = int(data["last_visit_year"])
    insurance_status = str(data["insurance_status"]).lower()

    years_since_visit = max(0, CURRENT_YEAR - last_visit_year)
    recency_factor = 1.0 + min(years_since_visit, 10) * 0.06
    insurance_factor = 0.45 if insurance_status == "insured" else 1.0
    subtotal = base * recency_factor * insurance_factor

    return {
        "service_type": "cleaning",
        "estimate_low": round(subtotal * 0.85, 2),
        "estimate_high": round(subtotal * 1.25, 2),
        "currency": "USD",
        "summary": f"Routine exam & cleaning for {data['patient_name']}",
        "disclaimer": ESTIMATE_DISCLAIMER,
        "patient_name": data["patient_name"],
        "contact_email": data["contact_email"],
        "last_visit_year": last_visit_year,
        "insurance_status": insurance_status,
        "preferred_time": str(data["preferred_time"]).lower(),
    }


def _estimate_emergency(data: dict[str, Any]) -> dict[str, Any]:
    base = 110.0
    issue_type = str(data["issue_type"]).lower()
    pain_level = int(data["pain_level"])
    insurance_status = str(data["insurance_status"]).lower()

    issue_factor = {"toothache": 1.35, "chipped_tooth": 1.2, "swelling": 1.5, "lost_filling": 0.95}[issue_type]
    pain_factor = 1.0 + pain_level * 0.02
    insurance_factor = 0.5 if insurance_status == "insured" else 1.0
    subtotal = base * issue_factor * pain_factor * insurance_factor

    return {
        "service_type": "emergency",
        "estimate_low": round(subtotal * 0.85, 2),
        "estimate_high": round(subtotal * 1.25, 2),
        "currency": "USD",
        "summary": f"Emergency dental visit for {data['patient_name']}",
        "disclaimer": ESTIMATE_DISCLAIMER,
        "patient_name": data["patient_name"],
        "contact_phone": data["contact_phone"],
        "issue_type": issue_type,
        "pain_level": pain_level,
        "insurance_status": insurance_status,
    }


def _estimate_cosmetic(data: dict[str, Any]) -> dict[str, Any]:
    treatment = str(data["treatment"]).lower()
    budget_band = str(data["budget_band"]).lower()
    timeline = str(data["timeline"]).lower()

    base = {"whitening": 350.0, "bonding": 450.0, "veneers": 1400.0, "aligners": 3600.0}[treatment]
    budget_factor = {"basic": 0.9, "standard": 1.0, "premium": 1.3}[budget_band]
    timeline_factor = {"asap": 1.1, "this_month": 1.0, "flexible": 0.95}[timeline]
    # Cosmetic treatment is self-pay; insurance never applies.
    subtotal = base * budget_factor * timeline_factor

    return {
        "service_type": "cosmetic",
        "estimate_low": round(subtotal * 0.85, 2),
        "estimate_high": round(subtotal * 1.15, 2),
        "currency": "USD",
        "summary": f"Cosmetic consultation ({treatment}) for {data['patient_name']}",
        "disclaimer": ESTIMATE_DISCLAIMER,
        "patient_name": data["patient_name"],
        "contact_email": data["contact_email"],
        "treatment": treatment,
        "budget_band": budget_band,
        "timeline": timeline,
    }
