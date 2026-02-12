from app.base_models import BaseTenantModel
"""
Base Model with common fields for all tables
"""
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.orm import declared_attr
from sqlalchemy.sql import func
from app.db import Base


class BaseModel(BaseTenantModel):
    """
    Base class for all models.
    Automatically adds id, created_at, and updated_at columns.
    """
    __abstract__ = True

    @declared_attr
    def id(cls):
        return Column(
            Integer,
            primary_key=True,
            autoincrement=True
        )

    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False
        )

    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False
        )
