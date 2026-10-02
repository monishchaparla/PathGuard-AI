"""Local Experiment Tracking for PathGuard-AI ML Pipeline.

Lightweight experiment tracker that logs training runs,
metrics, and model artifacts locally (no MLflow dependency).
"""
import json
import logging
import time
import uuid
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

@dataclass
class Experiment:
    experiment_id: str
    name: str
    model_size: str
    dataset: str
    config: Dict[str, Any]
    metrics: Dict[str, Any] = field(default_factory=dict)
    model_path: Optional[str] = None
    status: str = 'running'
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None
    notes: str = ''

class ExperimentTracker:
    def __init__(self, experiments_dir: str = 'experiments/'):
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(parents=True, exist_ok=True)
        self.experiments_file = self.experiments_dir / "experiments.json"
        
        if not self.experiments_file.exists():
            with open(self.experiments_file, 'w') as f:
                json.dump({}, f)

    def _load_experiments(self) -> Dict[str, Any]:
        with open(self.experiments_file, 'r') as f:
            return json.load(f)

    def _save_experiments(self, data: Dict[str, Any]):
        with open(self.experiments_file, 'w') as f:
            json.dump(data, f, indent=2)

    def start_experiment(self, name: str, model_size: str, dataset: str, config: Dict[str, Any]) -> Experiment:
        exp_id = str(uuid.uuid4())[:8]
        exp = Experiment(
            experiment_id=exp_id,
            name=name,
            model_size=model_size,
            dataset=dataset,
            config=config
        )
        
        data = self._load_experiments()
        data[exp_id] = asdict(exp)
        self._save_experiments(data)
        logger.info(f"Started experiment {name} ({exp_id})")
        return exp

    def log_metrics(self, experiment_id: str, metrics: Dict[str, Any]):
        data = self._load_experiments()
        if experiment_id in data:
            data[experiment_id]['metrics'].update(metrics)
            self._save_experiments(data)

    def log_epoch(self, experiment_id: str, epoch: int, metrics: Dict[str, Any]):
        data = self._load_experiments()
        if experiment_id in data:
            epoch_history = data[experiment_id]['metrics'].setdefault('history', {})
            epoch_history[str(epoch)] = metrics
            self._save_experiments(data)

    def finish_experiment(self, experiment_id: str, model_path: Optional[str] = None, final_metrics: Optional[Dict[str, Any]] = None):
        data = self._load_experiments()
        if experiment_id in data:
            if final_metrics:
                data[experiment_id]['metrics'].update(final_metrics)
            data[experiment_id]['model_path'] = model_path
            data[experiment_id]['status'] = 'completed'
            data[experiment_id]['finished_at'] = datetime.now().isoformat()
            self._save_experiments(data)
            logger.info(f"Finished experiment {experiment_id}")

    def get_experiment(self, experiment_id: str) -> Experiment:
        data = self._load_experiments()
        if experiment_id not in data:
            raise ValueError(f"Experiment {experiment_id} not found")
        return Experiment(**data[experiment_id])

    def list_experiments(self) -> List[Experiment]:
        data = self._load_experiments()
        return [Experiment(**exp_data) for exp_data in data.values()]

    def get_best_experiment(self, metric: str = 'mAP50') -> Optional[Experiment]:
        experiments = self.list_experiments()
        completed = [e for e in experiments if e.status == 'completed']
        if not completed:
            return None
            
        def get_metric(exp: Experiment) -> float:
            return exp.metrics.get(metric, 0.0)
            
        return max(completed, key=get_metric)

    def compare_experiments(self, exp_ids: List[str]) -> Dict[str, Any]:
        data = self._load_experiments()
        comparison = {}
        for eid in exp_ids:
            if eid in data:
                comparison[eid] = {
                    'name': data[eid]['name'],
                    'model_size': data[eid]['model_size'],
                    'dataset': data[eid]['dataset'],
                    'metrics': data[eid]['metrics']
                }
        return comparison

    def generate_report(self, experiment_id: str) -> str:
        exp = self.get_experiment(experiment_id)
        
        report = f"# Experiment Report: {exp.name}\n"
        report += f"**ID:** {exp.experiment_id} | **Status:** {exp.status}\n"
        report += f"**Model Size:** {exp.model_size} | **Dataset:** {exp.dataset}\n\n"
        
        report += "## Configuration\n"
        report += "```json\n" + json.dumps(exp.config, indent=2) + "\n```\n\n"
        
        report += "## Final Metrics\n"
        metrics_no_history = {k: v for k, v in exp.metrics.items() if k != 'history'}
        report += "```json\n" + json.dumps(metrics_no_history, indent=2) + "\n```\n\n"
        
        if exp.model_path:
            report += f"**Saved Model Path:** `{exp.model_path}`\n"
            
        return report
