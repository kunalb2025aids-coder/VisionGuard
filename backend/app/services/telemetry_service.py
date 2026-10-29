"""
Telemetry Service - Software-only sensor simulation system.
All readings are clearly marked source="simulation".
"""
import math
import random
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from backend.app.models.entities import TelemetryReading, Asset, AnomalyPrediction

logger = logging.getLogger("visionguard.telemetry")

# Sensor channel definitions: (unit, normal_min, normal_max, critical_min, critical_max)
SENSOR_CHANNELS: Dict[str, Dict] = {
    "temperature":       {"unit": "C",    "normal_min": 20.0, "normal_max": 55.0,  "warn_max": 65.0, "critical_max": 80.0},
    "vibration":         {"unit": "mm/s", "normal_min": 0.1,  "normal_max": 4.0,   "warn_max": 7.0,  "critical_max": 12.0},
    "motor_current":     {"unit": "A",    "normal_min": 8.0,  "normal_max": 18.0,  "warn_max": 22.0, "critical_max": 28.0},
    "belt_speed":        {"unit": "m/s",  "normal_min": 1.0,  "normal_max": 3.5,   "warn_max": 4.0,  "critical_max": 5.0},
    "bearing_temp":      {"unit": "C",    "normal_min": 25.0, "normal_max": 60.0,  "warn_max": 75.0, "critical_max": 90.0},
}

SCENARIOS: Dict[str, str] = {
    "normal":             "Normal operation — all sensors within range",
    "vibration_increase": "Gradual vibration increase — potential bearing wear",
    "temperature_anomaly":"Temperature spike — possible motor overheating",
    "belt_speed_variation":"Belt speed fluctuation — drive system irregularity",
    "combined_anomaly":   "Combined anomaly — multiple simultaneous faults",
}


class SimulationState:
    """Tracks per-asset simulation state."""
    def __init__(self, asset_code: str):
        self.asset_code = asset_code
        self.scenario: str = "normal"
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0
        self.step: int = 0
        self.seed: Optional[int] = None
        self._rng: Optional[random.Random] = None

    def reset(self, scenario: str = "normal", seed: Optional[int] = None):
        self.scenario = scenario
        self.step = 0
        self.seed = seed
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def rng(self) -> random.Random:
        if self._rng is None:
            self._rng = random.Random(self.seed)
        return self._rng


class TelemetryService:
    """
    Software-only configurable sensor simulation service.
    Produces deterministic readings for tests when seed is provided.
    """

    _instances: Dict[str, SimulationState] = {}

    @classmethod
    def get_state(cls, asset_code: str) -> SimulationState:
        if asset_code not in cls._instances:
            cls._instances[asset_code] = SimulationState(asset_code)
        return cls._instances[asset_code]

    @classmethod
    def list_scenarios(cls) -> Dict[str, str]:
        return SCENARIOS.copy()

    @classmethod
    def list_channels(cls) -> Dict[str, Dict]:
        return SENSOR_CHANNELS.copy()

    @classmethod
    def generate_reading(
        cls,
        asset_code: str,
        channel: str,
        scenario: str = "normal",
        step: int = 0,
        rng: Optional[random.Random] = None,
    ) -> Dict[str, Any]:
        """Generate a single sensor reading for the given scenario step."""
        if rng is None:
            rng = random.Random()
        cfg = SENSOR_CHANNELS.get(channel, {"unit": "?", "normal_min": 0, "normal_max": 100, "warn_max": 80, "critical_max": 100})
        base_min = cfg["normal_min"]
        base_max = cfg["normal_max"]
        warn_max = cfg["warn_max"]
        crit_max = cfg["critical_max"]

        # Base value: slow sinusoidal drift + noise
        t = step * 0.1
        noise = rng.gauss(0, (base_max - base_min) * 0.04)
        midpoint = (base_min + base_max) / 2.0
        amplitude = (base_max - base_min) * 0.2
        base_value = midpoint + amplitude * math.sin(t) + noise

        # Apply scenario modifications
        if scenario == "vibration_increase" and channel == "vibration":
            ramp = min(step * 0.15, 9.0)  # gradual increase
            base_value = base_min + ramp + abs(noise)
        elif scenario == "temperature_anomaly" and channel in ("temperature", "bearing_temp"):
            spike = min(step * 0.8, 35.0)
            base_value = midpoint + spike + noise
        elif scenario == "belt_speed_variation" and channel == "belt_speed":
            base_value = midpoint + amplitude * math.sin(t * 3) * 2.0 + noise
        elif scenario == "combined_anomaly":
            if channel == "vibration":
                base_value = min(base_min + step * 0.1 + abs(noise), crit_max)
            elif channel == "temperature":
                base_value = midpoint + min(step * 0.5, 25.0) + noise
            elif channel == "motor_current":
                base_value = base_max + min(step * 0.3, 12.0) + abs(noise)

        # Clamp to physical range
        hard_min = max(0.0, base_min * 0.5)
        hard_max = crit_max * 1.1
        value = max(hard_min, min(hard_max, base_value))

        threshold_breached = value > warn_max
        is_anomaly = value > warn_max

        return {
            "asset_code": asset_code,
            "sensor_channel": channel,
            "value": round(value, 3),
            "unit": cfg["unit"],
            "source": "simulation",
            "scenario": scenario,
            "is_anomaly": is_anomaly,
            "threshold_breached": threshold_breached,
            "thresholds": {
                "normal_min": base_min,
                "normal_max": base_max,
                "warn_max": warn_max,
                "critical_max": crit_max,
            },
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def generate_snapshot(
        cls,
        asset_code: str,
        scenario: str = "normal",
        step: int = 0,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generate one reading per channel for the given asset."""
        rng = random.Random(seed) if seed is not None else random.Random()
        readings = []
        for channel in SENSOR_CHANNELS:
            reading = cls.generate_reading(asset_code, channel, scenario, step, rng)
            readings.append(reading)
        return readings

    @classmethod
    def persist_snapshot(
        cls,
        db: Session,
        asset_id: int,
        asset_code: str,
        scenario: str = "normal",
        step: int = 0,
        seed: Optional[int] = None,
    ) -> List[TelemetryReading]:
        """Persist a telemetry snapshot to the database."""
        readings_data = cls.generate_snapshot(asset_code, scenario, step, seed)
        records = []
        for rd in readings_data:
            record = TelemetryReading(
                asset_id=asset_id,
                asset_code=asset_code,
                sensor_channel=rd["sensor_channel"],
                value=rd["value"],
                unit=rd["unit"],
                source="simulation",
                scenario=scenario,
                is_anomaly=rd["is_anomaly"],
                threshold_breached=rd["threshold_breached"],
            )
            db.add(record)
            records.append(record)
        db.commit()
        return records

    @classmethod
    def get_latest_readings(cls, db: Session, asset_code: str) -> List[Dict[str, Any]]:
        """Return the latest reading per channel for the given asset."""
        results = {}
        rows = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.asset_code == asset_code)
            .order_by(TelemetryReading.recorded_at.desc())
            .limit(50)
            .all()
        )
        for row in rows:
            if row.sensor_channel not in results:
                cfg = SENSOR_CHANNELS.get(row.sensor_channel, {})
                results[row.sensor_channel] = {
                    "sensor_channel": row.sensor_channel,
                    "value": row.value,
                    "unit": row.unit,
                    "source": row.source,
                    "scenario": row.scenario,
                    "is_anomaly": row.is_anomaly,
                    "threshold_breached": row.threshold_breached,
                    "thresholds": {
                        "normal_min": cfg.get("normal_min", 0),
                        "normal_max": cfg.get("normal_max", 100),
                        "warn_max": cfg.get("warn_max", 80),
                        "critical_max": cfg.get("critical_max", 100),
                    },
                    "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
                }
        return list(results.values())

    @classmethod
    def get_history(
        cls,
        db: Session,
        asset_code: str,
        channel: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return time-series history for the given asset/channel."""
        query = db.query(TelemetryReading).filter(TelemetryReading.asset_code == asset_code)
        if channel:
            query = query.filter(TelemetryReading.sensor_channel == channel)
        rows = query.order_by(TelemetryReading.recorded_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "sensor_channel": r.sensor_channel,
                "value": r.value,
                "unit": r.unit,
                "source": r.source,
                "scenario": r.scenario,
                "is_anomaly": r.is_anomaly,
                "threshold_breached": r.threshold_breached,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in reversed(rows)
        ]


# Global service instance
telemetry_service = TelemetryService()
