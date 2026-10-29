from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class DetectionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    defect_class: str
    confidence: float
    severity: str
    bbox: Optional[str] = None
    frame_number: Optional[int] = None
    created_at: Optional[datetime] = None

class InspectionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    media_type: str
    original_path: str
    result_path: Optional[str] = None
    status: str
    defects_count: int
    high_priority_count: int
    processing_time_ms: float
    created_at: datetime
    detections: List[DetectionSchema] = []

class DashboardSummarySchema(BaseModel):
    total_inspections: int = 0
    total_defects: int = 0
    high_priority_defects: int = 0
    completed_maintenance: int = 0
    pending_maintenance: int = 0
    defects_by_category: dict = {}
    defects_by_severity: dict = {}
    inspection_trends: list = []
    recent_inspections: List[InspectionSchema] = []

class MaintenanceTaskCreateSchema(BaseModel):
    inspection_id: Optional[int] = None
    detection_id: Optional[int] = None
    asset_id: Optional[str] = None
    component_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    defect_class: Optional[str] = "General Defect"
    severity: str = "Medium" # Low, Medium, High, Critical
    assigned_personnel: Optional[str] = "Unassigned"
    due_date: Optional[str] = None
    status: str = "Pending" # Pending, In Progress, Completed, Cancelled
    notes: Optional[str] = ""

class MaintenanceTaskUpdateSchema(BaseModel):
    title: Optional[str] = None
    severity: Optional[str] = None
    assigned_personnel: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class MaintenanceTaskSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_id: Optional[int] = None
    detection_id: Optional[int] = None
    asset_id: Optional[str] = None
    component_id: Optional[str] = None
    title: str
    defect_class: Optional[str] = None
    severity: str
    assigned_personnel: Optional[str] = None
    due_date: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AlertSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inspection_id: Optional[int] = None
    asset_id: Optional[str] = None
    title: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime

class HealthResponseSchema(BaseModel):
    status: str
    model_loaded: bool
    model_path: str
    database_connected: bool
    timestamp: datetime

# ─── Additive 2.0 Schemas ─────────────────────────────────────────

class ComponentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    component_id: str
    asset_id: str
    name: str
    component_type: str
    status: str
    health_score: float
    last_inspected: Optional[datetime] = None
    metadata_json: Optional[str] = None

class AssetSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    status: str
    health_score: float
    components: List[ComponentSchema] = []

class TelemetryReadingSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: str
    component_id: Optional[str] = None
    channel: str
    value: float
    unit: str
    source: str
    scenario: Optional[str] = None
    timestamp: datetime

class AnomalyPredictionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: str
    component_id: Optional[str] = None
    anomaly_type: str
    anomaly_score: float
    confidence: float
    severity: str
    model_version: str
    detection_method: str
    evidence_json: Optional[str] = None
    is_acknowledged: bool
    created_at: datetime

class CopilotAskRequestSchema(BaseModel):
    question: str = Field(..., min_length=2)
    asset_id: Optional[str] = None
    session_id: Optional[str] = None

class CopilotAskResponseSchema(BaseModel):
    answer: str
    evidence: List[Dict[str, Any]]
    session_id: str
    llm_source: str
    confidence: float
