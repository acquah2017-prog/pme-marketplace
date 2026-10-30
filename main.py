from enum import Enum
from typing import Optional
import hashlib

from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import jwt

DATABASE_URL = "sqlite:///./pme_marketplace.db"
SECRET_KEY = "cle_secrete_pme_ci_national_admin"
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="PME Marketplace Côte d'Ivoire - National Pro")
templates = Jinja2Templates(directory="templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed_password

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RoleEnum(str, Enum):
    commercant = "commercant"
    prestataire = "prestataire"
    admin = "admin"

class UserDB(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="commercant")

Base.metadata.create_all(bind=engine)

class UserCreate(BaseModel):
    nom: str
    email: str
    password: str
    role: Optional[RoleEnum] = RoleEnum.commercant

class UserResponse(BaseModel):
    id: int
    nom: str
    email: str
    role: str

    class Config:
        from_attributes = True

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/inscription-web", response_class=HTMLResponse)
def inscription_web(
    request: Request,
    nom: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(UserDB).filter(UserDB.email == email).first()
    if db_user:
        return templates.TemplateResponse("index.html", {
            "request": request, 
            "erreur": "Cet email est déjà utilisé."
        })
    
    hashed_pwd = hash_password(password)
    new_user = UserDB(nom=nom, email=email, hashed_password=hashed_pwd, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "succes": f"Félicitations {nom} ! Votre compte a été créé avec succès."
    })

@app.post("/utilisateurs/", response_model=UserResponse)
def inscrire_utilisateur(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Cet email est déjà enregistré")
    
    hashed_pwd = hash_password(user.password)
    new_user = UserDB(nom=user.nom, email=user.email, hashed_password=hashed_pwd, role=user.role.value)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    access_token = jwt.encode({"sub": user.email, "role": user.role}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}

