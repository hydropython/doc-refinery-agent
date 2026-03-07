"""
Configuration Tracking Module
Location: src/utils/config_tracker.py
"""

import hashlib
import yaml
import shutil
import json
from pathlib import Path
from datetime import datetime


def load_config(config_path: str = "rubric/extraction_rules.yaml") -> dict:
    """Load extraction rules config"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_config_hash(config_path: str) -> str:
    """Get SHA256 hash of config file for tracking"""
    with open(config_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def snapshot_config(config_path: str, output_dir: str, run_id: str) -> str:
    """Copy config file to output for audit trail"""
    config_snapshot_dir = Path(output_dir) / "config_snapshots"
    config_snapshot_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"config_{run_id}_{timestamp}.yaml"
    snapshot_path = config_snapshot_dir / snapshot_name
    
    shutil.copy2(config_path, snapshot_path)
    
    return str(snapshot_path)


def log_config_usage(run_id: str, config: dict, config_hash: str, 
                     snapshot_path: str, ledger_path: str = ".refinery/extraction_ledger.jsonl"):
    """Log config usage to extraction ledger"""
    Path(ledger_path).parent.mkdir(parents=True, exist_ok=True)
    
    log_entry = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "config_hash": config_hash,
        "config_snapshot": snapshot_path,
        "config_source": "rubric/extraction_rules.yaml",
        "strategy_thresholds": {
            "strategy_a": config.get("confidence", {}).get("strategy_a_threshold", 0.85),
            "strategy_b": config.get("confidence", {}).get("strategy_b_threshold", 0.75),
            "strategy_c": config.get("confidence", {}).get("strategy_c_threshold", 0.70)
        },
        "budget_guard": config.get("budget", {}).get("max_cost_per_document", 0.50)
    }
    
    with open(ledger_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    return log_entry
