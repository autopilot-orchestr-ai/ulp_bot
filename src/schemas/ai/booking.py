from pydantic import BaseModel, Field, field_validator


class BookingExtraction(BaseModel):
    consultation_type: str | None = None   # "legal" or "visa"
    duration_minutes: int | None = None    # 30 or 60
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    slot_choice: int | None = Field(default=None, ge=1, le=20)
    confirmed: bool | None = None
    wants_to_reschedule: bool = False
    reply: str = ""

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(filter(str.isdigit, v))
        if len(digits) < 9:
            raise ValueError("Phone number too short")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v.strip()) < 2:
            raise ValueError("Name too short")
        return v.strip()

    @field_validator("consultation_type")
    @classmethod
    def validate_consultation_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.lower().strip()
        if v not in ("legal", "visa"):
            return None
        return v

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, v: int | None) -> int | None:
        if v is None:
            return v
        if v not in (30, 60):
            return None
        return v