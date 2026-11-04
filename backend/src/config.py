import os

# Settings are read from environment variables (the .env file).
# The second value is the default, used if the variable is not set.
APP_ENV = os.getenv("APP_ENV", "development")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")