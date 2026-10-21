import os
from pathlib import Path

# Must run before the app is imported: tests use their own database and a known API key.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["API_KEY"] = "dev-key"
Path("test.db").unlink(missing_ok=True)