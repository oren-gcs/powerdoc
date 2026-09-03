from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    organization: str = Field(min_length=2)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    tenant_id: int
    is_active: bool
    is_blocked: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    is_active: bool
    is_suspended: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    status: str
    classification: str | None
    tags: list[Any]
    user_id: int
    tenant_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowStepIn(BaseModel):
    key: str
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class WorkflowIn(BaseModel):
    name: str
    description: str = ""
    trigger: str = "manual"
    is_active: bool = True
    steps: list[WorkflowStepIn]


class AutomationIn(BaseModel):
    name: str
    trigger_type: Literal["on_upload", "on_classify", "webhook", "schedule"]
    trigger_config: dict[str, Any] = Field(default_factory=dict)
    workflow_id: int
    is_active: bool = True


class NotifyIn(BaseModel):
    channel: str = "in_app"
    subject: str
    body: str
    user_id: int | None = None
    recipient_email: str | None = None


class ProcessFlags(BaseModel):
    enable_ocr: bool = True
    enable_workflow: bool = True
    enable_notification: bool = True
    enable_analytics: bool = True
    workflow_id: int | None = None
