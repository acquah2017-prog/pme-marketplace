cat << 'EOF' > database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Pour l'instant, on utilise une base SQLite locale (qui fonctionnera aussi sur Render, 
# mais qu'on pourra remplacer plus tard par PostgreSQL si besoin)
SQLALCHEMY_DATABASE_URL = "sqlite:///./marketplace.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
EOF

