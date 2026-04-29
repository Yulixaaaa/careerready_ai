# src/config/settings.py

class Settings:
    """
    Configuration settings for the application.
    """
    # Example PostgreSQL connection URL:
    # Replace with your actual database credentials
    # Format: postgresql://username:password@host:port/database_name
    DATABASE_URL = "postgresql://postgres:Ulyssa28@localhost:5432/Careerready"
    
    # You can add other settings here, like API keys for external services if needed
    # Example: OPENAI_API_KEY = "your_openai_api_key"

settings = Settings()