import os
from pathlib import Path

# Must run before the app is imported: tests use their own database and known credentials.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["API_KEY"] = "dev-key"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USER"] = "operator"
os.environ["ADMIN_PASSWORD"] = "test-pass"
Path("test.db").unlink(missing_ok=True)