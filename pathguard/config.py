import os
import yaml

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

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
        
        # Load .env file if present
        env_path = os.path.join(base_dir, '.env')
        if os.path.exists(env_path) and HAS_DOTENV:
            load_dotenv(env_path)
        
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

        # Direct Supabase and Database environment variable mappings
        if 'database' not in self.config:
            self.config['database'] = {}
            
        db = self.config['database']
        if os.getenv('SUPABASE_URL'):
            db['supabase_url'] = os.getenv('SUPABASE_URL')
        if os.getenv('SUPABASE_KEY'):
            db['supabase_key'] = os.getenv('SUPABASE_KEY')
        elif os.getenv('SUPABASE_ANON_KEY'):
            db['supabase_key'] = os.getenv('SUPABASE_ANON_KEY')
        elif os.getenv('SUPABASE_SERVICE_ROLE_KEY'):
            db['supabase_key'] = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
        if os.getenv('DATABASE_URL'):
            db['url'] = os.getenv('DATABASE_URL')
        elif os.getenv('SUPABASE_DB_URL'):
            db['url'] = os.getenv('SUPABASE_DB_URL')
            
        if os.getenv('DATABASE_HOST'):
            db['host'] = os.getenv('DATABASE_HOST')
        elif os.getenv('SUPABASE_DB_HOST'):
            db['host'] = os.getenv('SUPABASE_DB_HOST')
            
        if os.getenv('DATABASE_PORT'):
            db['port'] = int(os.getenv('DATABASE_PORT'))
        elif os.getenv('SUPABASE_DB_PORT'):
            db['port'] = int(os.getenv('SUPABASE_DB_PORT'))
            
        if os.getenv('DATABASE_PASSWORD'):
            db['password'] = os.getenv('DATABASE_PASSWORD')
        elif os.getenv('SUPABASE_DB_PASSWORD'):
            db['password'] = os.getenv('SUPABASE_DB_PASSWORD')
            
        if os.getenv('DATABASE_USER'):
            db['user'] = os.getenv('DATABASE_USER')
        elif os.getenv('SUPABASE_DB_USER'):
            db['user'] = os.getenv('SUPABASE_DB_USER')
            
        if os.getenv('DATABASE_NAME'):
            db['name'] = os.getenv('DATABASE_NAME')
        elif os.getenv('SUPABASE_DB_NAME'):
            db['name'] = os.getenv('SUPABASE_DB_NAME')
            
        if os.getenv('DATABASE_SSLMODE'):
            db['sslmode'] = os.getenv('DATABASE_SSLMODE')

_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader().config
    return _config_instance
