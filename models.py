from typing import List, Optional
from datetime import date
from sqlalchemy import ForeignKey, String, Date, Vector, Text, Boolean, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class Expert(Base):
    __tablename__ = "expert"

    class Status:
        pending = 'pending'
        active = 'active'
        inactive = 'inactive'


    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(Text())
    status: Mapped[bool] = mapped_column(Boolean())

    experiences: Mapped[List["Experience"]] = relationship(
        back_populates="expert", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Expert(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"
    

class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("expert.id"), nullable=False)
    expert: Mapped["Expert"] = relationship(back_populates="experiences")

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    summary: Mapped[str] = mapped_column(Text())

    attributes: Mapped[List["Attribute"]] = relationship(
        back_populates="experience", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Experience(id={self.id!r}, name={self.name!r}, start_date={self.start_date!r}, end_date={self.end_date!r})"


class Attribute(Base):
    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text())

    embedding = mapped_column(Vector(256))

    def __repr__(self) -> str:
        return f"Attribute(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"