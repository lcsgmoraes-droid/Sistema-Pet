from app.config import get_database_url
import os

print("DATABASE_TYPE:", os.getenv("DATABASE_TYPE"))
print("POSTGRES_HOST:", os.getenv("POSTGRES_HOST"))  
print("RUNNING_IN_DOCKER:", os.getenv("RUNNING_IN_DOCKER"))
print("DATABASE_URL:", get_database_url())
