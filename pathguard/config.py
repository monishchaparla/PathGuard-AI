import os
import yaml

class AttrDict(dict):
    """A dictionary that allows for attribute-style access."""
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
        for key, value in self.items():
            if isinstance(value, dict):
                self[key] = AttrDict(value)

class ConfigLoader:
    def __init__(self):
        self.config = AttrDict()
        self._load_config()

    def _load_config(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Load default config
        default_config_path = os.path.join(base_dir, 'config', 'default_config.yaml')
        if os.path.exists(default_config_path):
            with open(default_config_path, 'r') as f:
                self._update_dict(self.config, yaml.safe_load(f) or {})
                
        # Load local config
        local_config_path = os.path.join(base_dir, 'config', 'local_config.yaml')
        if os.path.exists(local_config_path):
            with open(local_config_path, 'r') as f:
                self._update_dict(self.config, yaml.safe_load(f) or {})
                
        # Load environment variables
        self._load_env_vars()
        
        # Convert to AttrDict for dot notation access
        self.config = AttrDict(self.config)

    def _update_dict(self, target, source):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._update_dict(target[k], v)
            else:
                target[k] = v

    def _load_env_vars(self):
        prefix = 'PATHGUARD_'
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # E.g., PATHGUARD_DATABASE_HOST -> database.host
                config_key = key[len(prefix):].lower()
                parts = config_key.split('_')
                
                # Navigate and set
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Simple type casting
                if value.lower() in ('true', 'false'):
                    current[parts[-1]] = value.lower() == 'true'
                elif value.isdigit():
                    current[parts[-1]] = int(value)
                else:
                    try:
                        current[parts[-1]] = float(value)
                    except ValueError:
                        current[parts[-1]] = value

_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader().config
    return _config_instance
