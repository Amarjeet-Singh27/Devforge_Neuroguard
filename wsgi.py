import os

from app import create_app


config_name = os.environ.get("APP_CONFIG", "production")
app = create_app(config_name)
