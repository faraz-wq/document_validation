"""
SQLAlchemy ORM models for the Document Validation Service
Replaces the previous SQLite-based approach with proper ORM models
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON, LargeBinary
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


# ==============================================================================
# Authentication & User Management
# ==============================================================================

class User(Base):
    """User accounts for the system"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for API-key-only users
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")
    schemas = relationship("SchemaDefinition", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """API keys for authentication and usage tracking"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    # Usage tracking fields (Feature 1: Observability)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    total_requests = Column(Integer, default=0, nullable=False)
    total_errors = Column(Integer, default=0, nullable=False)
    total_documents = Column(Integer, default=0, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="api_keys")
    sessions = relationship("Session", back_populates="api_key", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="api_key", cascade="all, delete-orphan")


# ==============================================================================
# Observability & Monitoring (Feature 1)
# ==============================================================================

class RequestLog(Base):
    """Per-request logging for observability and monitoring"""
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="SET NULL"), index=True, nullable=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    
    # Request details
    path = Column(String(500), index=True, nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    processing_ms = Column(Float, nullable=False)
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)
    client_ip = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    api_key = relationship("ApiKey", back_populates="request_logs")
    session = relationship("Session", back_populates="request_logs")


# ==============================================================================
# Schema Management (Feature 2)
# ==============================================================================

class SchemaDefinition(Base):
    """Custom extraction schemas defined by users"""
    __tablename__ = "schema_definitions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    definition_json = Column(JSON, nullable=False)  # Stores the complete schema structure
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="schemas")


# ==============================================================================
# Document Processing Sessions
# ==============================================================================

class Session(Base):
    """Document processing sessions"""
    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=True, index=True)
    application_type = Column(String(100), nullable=False)
    summary_json = Column(JSON, nullable=False)
    token_usage_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")
    api_key = relationship("ApiKey", back_populates="sessions")
    documents = relationship("Document", back_populates="session", cascade="all, delete-orphan")
    bounding_boxes = relationship("BoundingBox", back_populates="session", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="session", cascade="all, delete-orphan")
    request_logs = relationship("RequestLog", back_populates="session")


class Document(Base):
    """Uploaded documents associated with sessions"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Path to file on disk
    mime_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    session = relationship("Session", back_populates="documents")


class BoundingBox(Base):
    """Bounding box coordinates for extracted fields"""
    __tablename__ = "bounding_boxes"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    document_title = Column(String(255), nullable=True)
    page = Column(Integer, nullable=False)
    coordinates = Column(JSON, nullable=False)  # [y_min, x_min, y_max, x_max]

    # Relationships
    session = relationship("Session", back_populates="bounding_boxes")


class Citation(Base):
    """Citations mapping fields to their source documents"""
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    field_name = Column(String(255), nullable=False)
    citation = Column(Text, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="citations")


# ==============================================================================
# Validation Sessions (Form Validation Feature)
# ==============================================================================

class ValidationSession(Base):
    """Validation sessions for form validation workflow"""
    __tablename__ = "validation_sessions"

    validation_id = Column(String(36), primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Link to extraction session if validation was done on extracted data
    extraction_session_id = Column(String(36), ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Application details
    application_type = Column(String(100), nullable=False, index=True)
    
    # Validation results
    validation_report_json = Column(JSON, nullable=False)  # Complete ValidationReport
    extraction_summary_json = Column(JSON, nullable=False)  # The data that was validated
    
    # Validation metadata
    auto_approved = Column(Boolean, nullable=False, index=True)
    confidence_score = Column(Float, nullable=False)
    error_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    user = relationship("User")
    api_key = relationship("ApiKey")
    extraction_session = relationship("Session")
