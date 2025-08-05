from typing import List, Optional
from datetime import date
from sqlalchemy import ForeignKey, String, Date, Text, Boolean, Enum, Index, JSON, event, Table, Column, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass

# Association table for many-to-many relationship between Experience and Attribute
experience_attribute_association = Table(
    'experience_attribute',
    Base.metadata,
    Column('experience_id', Integer, ForeignKey('experience.id'), primary_key=True),
    Column('attribute_id', Integer, ForeignKey('attribute.id'), primary_key=True)
)

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
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    experiences: Mapped[List["Experience"]] = relationship(
        back_populates="expert", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Expert(id={self.id!r}, name={self.name!r}, summary={self.summary!r})"
    

class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    expert_id: Mapped[int] = mapped_column(ForeignKey("expert.id"), nullable=False)
    expert: Mapped["Expert"] = relationship(back_populates="experiences")

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    summary: Mapped[str] = mapped_column(Text())

    attributes: Mapped[List["Attribute"]] = relationship(
        secondary=experience_attribute_association,
        back_populates="experiences"
    )

    def __repr__(self) -> str:
        return f"Experience(id={self.id!r}, summary={self.summary!r}, start_date={self.start_date!r}, end_date={self.end_date!r})"


class Attribute(Base):
    __tablename__ = "attribute"
    __table_args__ = (
        Index('ix_attribute_type', 'type'),
        Index('ix_attribute_type_name', 'type', 'name', unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("attribute.id"), nullable=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text())
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)  # OpenAI embeddings are 1536 dimensions

    # Self-referential relationship for taxonomy
    parent: Mapped[Optional["Attribute"]] = relationship("Attribute", remote_side=[id], back_populates="children")
    children: Mapped[List["Attribute"]] = relationship("Attribute", back_populates="parent", cascade="all, delete-orphan")

    experiences: Mapped[List["Experience"]] = relationship(
        secondary=experience_attribute_association,
        back_populates="attributes"
    )

    def __repr__(self) -> str:
        return f"Attribute(id={self.id!r}, name={self.name!r}, type={self.type!r})"

# Event listeners for automatic embedding generation
@event.listens_for(Attribute, 'before_insert')
def generate_embedding_before_insert(mapper, connection, target):
    """Generate embedding before inserting a new Attribute if not already set"""
    if target.embedding is None:
        try:
            from lib.embedding_service import embedding_service
            target.embedding = embedding_service.generate_attribute_embedding(
                target.name, target.type, target.summary
            )
        except Exception as e:
            # Log the error but don't fail the insert
            print(f"Warning: Failed to generate embedding for attribute {target.name}: {str(e)}")

@event.listens_for(Attribute, 'before_update')
def generate_embedding_before_update(mapper, connection, target):
    """Generate new embedding before updating if content changed and embedding not manually set"""
    # Check if any content fields changed and embedding wasn't manually updated
    if hasattr(target, '_sa_instance_state'):
        history = target._sa_instance_state
        name_changed = 'name' in history.attrs and history.attrs['name'].history.has_changes()
        type_changed = 'type' in history.attrs and history.attrs['type'].history.has_changes()
        summary_changed = 'summary' in history.attrs and history.attrs['summary'].history.has_changes()
        embedding_changed = 'embedding' in history.attrs and history.attrs['embedding'].history.has_changes()
        
        # If content changed but embedding wasn't manually updated, regenerate it
        if (name_changed or type_changed or summary_changed) and not embedding_changed:
            try:
                from lib.embedding_service import embedding_service
                target.embedding = embedding_service.generate_attribute_embedding(
                    target.name, target.type, target.summary
                )
            except Exception as e:
                print(f"Warning: Failed to update embedding for attribute {target.name}: {str(e)}")