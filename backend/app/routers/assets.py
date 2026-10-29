"""Assets & Components API - manages conveyor belt equipment records."""
import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.database import get_db
from backend.app.models.entities import Asset, Component, Inspection, Detection, MaintenanceTask

router = APIRouter(prefix="/api/assets", tags=["Assets"])
logger = logging.getLogger("visionguard.assets")

# Default assets seeded on first access
DEFAULT_ASSETS = [
    {
        "asset_id": "CONV-01",
        "name": "Conveyor Line 01",
        "description": "Primary coal transport conveyor, 120m length",
        "location": "Plant A - Section 1",
        "components": [
            {"component_id": "CONV-01-BELT",       "name": "Main Drive Belt",     "component_type": "belt"},
            {"component_id": "CONV-01-ROLLER-01",  "name": "Head Roller",         "component_type": "roller"},
            {"component_id": "CONV-01-ROLLER-02",  "name": "Tail Roller",         "component_type": "roller"},
            {"component_id": "CONV-01-ROLLER-03",  "name": "Carry Idler Set A",   "component_type": "idler"},
            {"component_id": "CONV-01-MOTOR-01",   "name": "Drive Motor",         "component_type": "motor"},
            {"component_id": "CONV-01-FRAME",      "name": "Support Frame",       "component_type": "frame"},
        ],
    },
    {
        "asset_id": "CONV-02",
        "name": "Conveyor Line 02",
        "description": "Secondary product discharge conveyor, 80m length",
        "location": "Plant A - Section 2",
        "components": [
            {"component_id": "CONV-02-BELT",       "name": "Main Drive Belt",     "component_type": "belt"},
            {"component_id": "CONV-02-ROLLER-01",  "name": "Head Roller",         "component_type": "roller"},
            {"component_id": "CONV-02-ROLLER-02",  "name": "Tail Roller",         "component_type": "roller"},
            {"component_id": "CONV-02-MOTOR-01",   "name": "Drive Motor",         "component_type": "motor"},
            {"component_id": "CONV-02-FRAME",      "name": "Support Frame",       "component_type": "frame"},
        ],
    },
    {
        "asset_id": "CONV-03",
        "name": "Conveyor Line 03",
        "description": "Bulk material intake conveyor, 200m length",
        "location": "Plant B - Main Hall",
        "components": [
            {"component_id": "CONV-03-BELT",       "name": "Main Drive Belt",     "component_type": "belt"},
            {"component_id": "CONV-03-ROLLER-01",  "name": "Head Roller",         "component_type": "roller"},
            {"component_id": "CONV-03-ROLLER-02",  "name": "Carry Idler Set A",   "component_type": "idler"},
            {"component_id": "CONV-03-ROLLER-03",  "name": "Return Idler Set A",  "component_type": "idler"},
            {"component_id": "CONV-03-MOTOR-01",   "name": "Drive Motor",         "component_type": "motor"},
            {"component_id": "CONV-03-FRAME",      "name": "Support Frame",       "component_type": "frame"},
        ],
    },
]

def seed_assets(db: Session):
    """Seed default assets if none exist."""
    if db.query(Asset).count() > 0:
        return
    for a_data in DEFAULT_ASSETS:
        asset = Asset(
            asset_id=a_data["asset_id"],
            name=a_data["name"],
            description=a_data.get("description"),
            location=a_data.get("location"),
            status="operational",
            health_score=100.0,
        )
        db.add(asset)
        db.flush()
        for c_data in a_data.get("components", []):
            comp = Component(
                component_id=c_data["component_id"],
                asset_id=asset.id,
                name=c_data["name"],
                component_type=c_data["component_type"],
                status="healthy",
                health_score=100.0,
            )
            db.add(comp)
    db.commit()
    logger.info(f"Seeded {len(DEFAULT_ASSETS)} default assets.")


def asset_to_dict(asset: Asset) -> dict:
    return {
        "id": asset.id,
        "asset_id": asset.asset_id,
        "name": asset.name,
        "description": asset.description,
        "location": asset.location,
        "status": asset.status,
        "health_score": asset.health_score,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


def component_to_dict(comp: Component) -> dict:
    return {
        "id": comp.id,
        "component_id": comp.component_id,
        "asset_id": comp.asset_id,
        "name": comp.name,
        "component_type": comp.component_type,
        "status": comp.status,
        "health_score": comp.health_score,
        "last_inspected": comp.last_inspected.isoformat() if comp.last_inspected else None,
        "notes": comp.notes,
    }


@router.get("", response_model=List[dict])
def list_assets(db: Session = Depends(get_db)):
    """List all conveyor assets. Seeds defaults if DB is empty."""
    seed_assets(db)
    assets = db.query(Asset).order_by(Asset.asset_id).all()
    return [asset_to_dict(a) for a in assets]


@router.get("/{asset_id_code}", response_model=dict)
def get_asset(asset_id_code: str, db: Session = Depends(get_db)):
    seed_assets(db)
    asset = db.query(Asset).filter(Asset.asset_id == asset_id_code).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id_code}' not found")
    d = asset_to_dict(asset)
    d["components"] = [component_to_dict(c) for c in asset.components]
    return d


@router.get("/{asset_id_code}/components", response_model=List[dict])
def get_asset_components(asset_id_code: str, db: Session = Depends(get_db)):
    seed_assets(db)
    asset = db.query(Asset).filter(Asset.asset_id == asset_id_code).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id_code}' not found")
    return [component_to_dict(c) for c in asset.components]


@router.get("/{asset_id_code}/summary", response_model=dict)
def get_asset_summary(asset_id_code: str, db: Session = Depends(get_db)):
    """Return summary including inspection and maintenance context for the asset."""
    seed_assets(db)
    asset = db.query(Asset).filter(Asset.asset_id == asset_id_code).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id_code}' not found")

    # Fetch recent inspections (all inspections linked to this asset)
    recent_inspections = (
        db.query(Inspection).order_by(Inspection.created_at.desc()).limit(5).all()
    )
    open_tasks = (
        db.query(MaintenanceTask)
        .filter(MaintenanceTask.status.in_(["Pending", "In Progress"]))
        .count()
    )

    return {
        "asset": asset_to_dict(asset),
        "components": [component_to_dict(c) for c in asset.components],
        "recent_inspections_count": len(recent_inspections),
        "open_maintenance_tasks": open_tasks,
        "note": "Inspections are not yet linked to specific assets. Future versions will add asset_id FK to inspections.",
    }


@router.get("/components/{component_id_code}", response_model=dict)
def get_component(component_id_code: str, db: Session = Depends(get_db)):
    seed_assets(db)
    comp = db.query(Component).filter(Component.component_id == component_id_code).first()
    if not comp:
        raise HTTPException(status_code=404, detail=f"Component '{component_id_code}' not found")
    d = component_to_dict(comp)
    # Add maintenance context
    open_tasks = (
        db.query(MaintenanceTask)
        .filter(MaintenanceTask.status.in_(["Pending", "In Progress"]))
        .count()
    )
    d["open_maintenance_tasks"] = open_tasks
    d["note"] = "Defect-to-component mapping is illustrative. Actual 2D bounding boxes cannot be reliably mapped to 3D component coordinates automatically."
    return d
