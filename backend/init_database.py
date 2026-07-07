from sqlalchemy import inspect

from src.database.database import Base, engine
from src.database.models import (
    AdminUser,
    Chat,
    Message,
    User,
)


print("Creating ProspectusAI database tables...")

Base.metadata.create_all(bind=engine)

tables = inspect(engine).get_table_names()

print("\n=== DATABASE READY ===")

for table in sorted(tables):
    print(table)
