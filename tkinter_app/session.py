"""In-memory session for the signed-in user."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Session:
    user_id: int
    username: str
    role: str
    student_id: Optional[str]
    must_change_password: bool

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @classmethod
    def from_user_row(cls, row: dict[str, Any]) -> "Session":
        return cls(
            user_id=int(row["id"]),
            username=row["username"],
            role=row["role"],
            student_id=row["student_id"],
            must_change_password=bool(row["must_change_password"]),
        )
