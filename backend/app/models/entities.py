from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.models.database import Base

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    media_type = Column(String(50), nullable=False, default="image")
    original_path = Column(String(500), nullable=False)
    result_path = Column(String(500), nullable=True)
    status = Column(String(50), nullable=False, default="completed")
    defects_count = Column(Integer, default=0)
    high_priority_count = Column(Integer, default=0)
    processing_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    detections = relationship("Detection", back_populates="inspection", cascade="all, delete-orphan")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="inspection")
    alerts = relationship("Alert", back_populates="inspection")

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False)
    defect_class = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String(50), nullable=False, default="Medium")
    bbox = Column(String(255), nullable=True)
    frame_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="detections")
    maintenance_tasks = relationship("MaintenanceTask", back_populates="detection")

class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True)
    detection_id = Column(Integer, ForeignKey("detections.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    defect_class = Column(String(100), nullable=True)
    severity = Column(String(50), nullable=False, default="Medium")
    assigned_personnel = Column(String(100), nullable=True, default="Unassigned")
    due_date = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="Pending")
    notes = Column(Text, nullable=True)
    audit_log = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="maintenance_tasks")
    detection = relationship("Detection", back_populates="maintenance_tasks")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(50), nullable=False, default="High")
    is_read = Column(Boolean, default=False)
    suppressed = Column(Boolean, default=False)
    source = Column(String(100), nullable=True, default="detection")
    created_at = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("Inspection", back_populates="alerts")

class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# NEW: Asset Management

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="operational")
    health_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    components = relationship("Component", back_populates="asset", cascade="all, delete-orphan")
    telemetry_readings = relationship("TelemetryReading", back_populates="asset")

class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    component_id = Column(String(100), unique=True, nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    component_type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="healthy")
    health_score = Column(Float, default=100.0)
    last_inspected = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset", back_populates="components")

# NEW: Sensor Telemetry

class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    asset_code = Column(String(50), nullable=False)
    sensor_channel = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True)
    source = Column(String(50), nullable=False, default="simulation")
    scenario = Column(String(100), nullable=True)
    is_anomaly = Column(Boolean, default=False)
    threshold_breached = Column(Boolean, default=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)

    asset = relationship("Asset", back_populates="telemetry_readings")

# NEW: Anomaly Predictions

class AnomalyPrediction(Base):
    __tablename__ = "anomaly_predictions"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    asset_code = Column(String(50), nullable=False)
    prediction_type = Column(String(100), nullable=False)
    sensor_channel = Column(String(100), nullable=True)
    anomaly_score = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    evidence = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False, default="Medium")
    status = Column(String(50), nullable=False, default="open")
    model_version = Column(String(50), nullable=True)
    source = Column(String(50), nullable=False, default="simulation")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

# NEW: AI Copilot Sessions

class CopilotSession(Base):
    __tablename__ = "copilot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=True)
    evidence_sources = Column(Text, nullable=True)
    provider = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
