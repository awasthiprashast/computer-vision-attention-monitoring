import os

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://attention:attention@localhost:5432/attentiondb"
)
# When unset, authentication is disabled (local development only).
API_KEY = os.environ.get("API_KEY", "")
