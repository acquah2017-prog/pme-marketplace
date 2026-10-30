from enum import Enum
from typing import Optional
import hashlib

from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
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

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})

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
        return templates.TemplateResponse(request, "index.html", {
            "request": request,
            "erreur": "Cet email est déjà utilisé."
        })
    
    hashed_pwd = hash_password(password)
    new_user = UserDB(nom=nom, email=email, hashed_password=hashed_pwd, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "succes": f"Félicitations {nom} ! Votre compte a été créé avec succès."
    })

# Route d'affichage de la page de connexion Admin
@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_get(request: Request):
    return templates.TemplateResponse(request, "admin_login.html", {})

# Traitement de la connexion Admin
@app.post("/admin-login", response_class=HTMLResponse)
def admin_login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if not user or not verify_password(password, user.hashed_password) or user.role != "admin":
        return templates.TemplateResponse(request, "admin_login.html", {
            "erreur": "Identifiants incorrects ou accès non autorisé (Admin uniquement)."
        })
    
    # Si c'est un admin valide, on affiche le tableau de bord avec les utilisateurs
    utilisateurs = db.query(UserDB).all()
    return templates.TemplateResponse(request, "admin.html", {
        "utilisateurs": utilisateurs
    })

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    utilisateurs = db.query(UserDB).all()
    return templates.TemplateResponse(request, "admin.html", {
        "utilisateurs": utilisateurs
    })

