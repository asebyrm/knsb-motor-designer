"""Pydantic v2 request/response models for the API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

# --- auth ---------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=10, max_length=200)
    locale: Literal["tr", "en"] = "en"


class LoginRequest(BaseModel):
    email_or_username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    role: str
    locale: str
    email_verified: bool


# --- designs ---------------------------------------------------------

class DesignIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    config_json: dict[str, Any]
    visibility: Literal["private", "unlisted", "public"] = "private"


class DesignOut(BaseModel):
    id: str
    name: str
    description: str
    config_json: dict[str, Any]
    visibility: str
    slug: str | None
    fork_of_id: str | None
    owner_username: str | None
    created_at: str
    updated_at: str


# --- simulation / mission ---------------------------------------------

class SimulateRequest(BaseModel):
    design: dict[str, Any]
    downsample: int = Field(default=500, ge=50, le=2000)


class MissionRequest(BaseModel):
    dry_mass: float = Field(gt=0)
    body_diameter: float = Field(gt=0)
    target_apogee: float = Field(gt=0)
    drag_coefficient: float = 0.55
    rail_length: float = 2.0
    launch_altitude: float = 0.0
    max_accel_g: float = 15.0
    case_inner_diameter: float = 0.075
    case_wall_thickness: float = 0.004
    case_material_id: str = "pa12"
    print_method: Literal["fdm", "sls", "machined"] = "sls"
    liner_material_id: str = "kraft_phenolic"
    liner_thickness: float = 0.003
    propellant_id: str = "knsb"
    meop_bar: float = 40.0
    time_budget_s: float = Field(default=30.0, ge=5.0, le=60.0)


class JobOut(BaseModel):
    job_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str = ""


class ExportRequest(BaseModel):
    design: dict[str, Any]
    fmt: Literal["eng", "rse", "csv", "json", "pdf", "svg", "nozzle_csv"]
    locale: Literal["tr", "en"] = "en"
    accept_risk: bool = False


TokenResponse.model_rebuild()
