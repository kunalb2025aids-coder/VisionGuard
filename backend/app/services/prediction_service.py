"""
Prediction Service - Explainable anomaly detection using threshold rules
and optionally scikit-learn IsolationForest when sufficient data exists.
Keeps visual defect detection (YOLO), sensor anomaly detection, and
failure prediction as three clearly distinct concepts.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("visionguard.predictions")

SKLEARN_AVAILABLE = False
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    SKLEARN_AVAILABLE = True
    logger.info("scikit-learn available for IsolationForest anomaly detection.")
except ImportError:
    logger.info("scikit-learn not installed. Using threshold-only anomaly detection.")

from backend.app.services.telemetry_service import SENSOR_CHANNELS


class PredictionService:
    """
    Anomaly indicator service.
    - Threshold-based: always available (no trained model needed)
    - IsolationForest: optional, requires scikit-learn + sufficient history
    """

    MODEL_VERSION = "threshold-v1.0"
    SKLEARN_VERSION = "isolation-forest-v1.0" if SKLEARN_AVAILABLE else None
    MIN_SAMPLES_FOR_ML = 30  # Minimum history points before attempting ML

    @classmethod
    def status(cls) -> Dict[str, Any]:
        return {
            "threshold_model": {
                "available": True,
                "version": cls.MODEL_VERSION,
                "description": "Rule-based threshold anomaly indicator",
            },
            "ml_model": {
                "available": SKLEARN_AVAILABLE,
                "version": cls.SKLEARN_VERSION,
                "description": "scikit-learn IsolationForest (requires sufficient telemetry history)",
                "min_samples_required": cls.MIN_SAMPLES_FOR_ML,
                "note": (
                    "Model is NOT a validated failure predictor. A threshold breach "
                    "generates an anomaly indicator, not a statistically validated "
                    "prediction of equipment failure."
                ),
            },
        }

    @classmethod
    def analyze_readings(cls, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze a list of telemetry readings for threshold breaches.
        Returns list of anomaly indicators with evidence.
        """
        indicators = []
        for reading in readings:
            channel = reading.get("sensor_channel", "")
            value = reading.get("value", 0)
            cfg = SENSOR_CHANNELS.get(channel, {})
            warn_max = cfg.get("warn_max", float("inf"))
            crit_max = cfg.get("critical_max", float("inf"))
            normal_min = cfg.get("normal_min", 0)
            normal_max = cfg.get("normal_max", 100)

            if value > crit_max:
                severity = "Critical"
                breach = "critical_max"
            elif value > warn_max:
                severity = "High"
                breach = "warn_max"
            elif value < normal_min:
                severity = "Medium"
                breach = "below_normal_min"
            else:
                continue  # No anomaly

            evidence = {
                "type": "threshold_breach",
                "channel": channel,
                "value": value,
                "threshold_type": breach,
                "threshold_value": warn_max if breach == "warn_max" else crit_max,
                "unit": cfg.get("unit", ""),
                "note": (
                    "This is a threshold breach indicator, not a statistically validated "
                    "prediction of equipment failure. Engineer review required."
                ),
            }

            indicators.append({
                "prediction_type": "threshold_breach",
                "sensor_channel": channel,
                "actual_value": value,
                "threshold_value": warn_max,
                "anomaly_score": None,
                "severity": severity,
                "evidence": json.dumps(evidence),
                "model_version": cls.MODEL_VERSION,
                "source": reading.get("source", "simulation"),
            })

        return indicators

    @classmethod
    def run_isolation_forest(
        cls,
        history: List[Dict[str, Any]],
        latest: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Run IsolationForest on historical data if sklearn is available
        and sufficient history exists.
        Returns anomaly indicator dict or None.
        """
        if not SKLEARN_AVAILABLE:
            return None

        channel = latest.get("sensor_channel")
        channel_history = [
            h["value"] for h in history if h.get("sensor_channel") == channel
        ]

        if len(channel_history) < cls.MIN_SAMPLES_FOR_ML:
            return None

        try:
            values = np.array(channel_history).reshape(-1, 1)
            clf = IsolationForest(contamination=0.1, random_state=42)
            clf.fit(values)
            score = float(clf.score_samples([[latest["value"]]])[0])
            is_anomaly = clf.predict([[latest["value"]]])[0] == -1

            if is_anomaly:
                evidence = {
                    "type": "isolation_forest",
                    "channel": channel,
                    "value": latest["value"],
                    "anomaly_score": score,
                    "training_samples": len(channel_history),
                    "note": (
                        "IsolationForest anomaly indicator based on historical sensor data. "
                        "NOT a validated failure prediction. Engineer review required."
                    ),
                }
                return {
                    "prediction_type": "isolation_forest",
                    "sensor_channel": channel,
                    "actual_value": latest["value"],
                    "threshold_value": None,
                    "anomaly_score": score,
                    "severity": "Medium",
                    "evidence": json.dumps(evidence),
                    "model_version": cls.SKLEARN_VERSION,
                    "source": latest.get("source", "simulation"),
                }
        except Exception as e:
            logger.error(f"IsolationForest error: {e}")
        return None


prediction_service = PredictionService()
