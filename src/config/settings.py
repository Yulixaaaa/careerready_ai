import os

class Settings:
    """
    Configuration settings for the application.
    """
    # 1. Kuhaon ang DATABASE_URL gikan sa Render Environment Variable
    # 2. Kung wala (local computer), mogamit siya sa imong localhost
    DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:Ulyssa28@localhost:5432/Careerready"
    )
    
    # 3. Importante: Ang Render naggamit og 'postgres://' pero SQLAlchemy kinahanglan 'postgresql://'
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

settings = Settings()