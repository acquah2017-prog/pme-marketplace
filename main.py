from enum import Enum
from typing import Optional
import hashlib

from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./pme_marketplace.db"
SECRET_KEY = "cle_secrete_pme_ci_national_admin"
ALGORITHM = "HS256"

# Tes coordonnées d'administrateur unique
ADMIN_EMAIL = "acquah2017@gmail.com"
ADMIN_PASSWORD = "Cancer1993."

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="PME Marketplace Côte d'Ivoire - National Pro")
templates = Jinja2Templates(directory="templates")

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

class UserDB(Base):
    __tablename__ = "utilisateurs"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="commercant")

Base.metadata.create_all(bind=engine)

def init_admin():
    db = SessionLocal()
    admin_user = db.query(UserDB).filter(UserDB.email == ADMIN_EMAIL).first()
    if not admin_user:
        new_admin = UserDB(
            nom="Administrateur Principal",
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role="admin"
        )
        db.add(new_admin)
        db.commit()
    else:
        admin_user.hashed_password = hash_password(ADMIN_PASSWORD)
        admin_user.role = "admin"
        db.commit()
    db.close()

init_admin()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})

@app.post("/inscription-web", response_class=HTMLResponse)
def inscription_web(
    request: Request,
    nom: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    if email.lower() == ADMIN_EMAIL.lower():
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"erreur": "Cet email est réservé à l'administration."}
        )

    db_user = db.query(UserDB).filter(UserDB.email == email).first()
    if db_user:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"erreur": "Cet email est déjà utilisé."}
        )
    
    hashed_pwd = hash_password(password)
    new_user = UserDB(nom=nom, email=email, hashed_password=hashed_pwd, role=role)
    db.add(new_user)
    db.commit()
    
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"succes": f"Félicitations {nom} ! Votre compte a été créé avec succès."}
    )

@app.get("/admin-login", response_class=HTMLResponse)
def admin_login_get(request: Request):
    return templates.TemplateResponse(request=request, name="admin_login.html", context={})

@app.post("/admin-login", response_class=HTMLResponse)
def admin_login_post(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    if email.strip().lower() != ADMIN_EMAIL.lower() or password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"erreur": "Accès refusé : Identifiants administrateur incorrects."}
        )
    
    # Redirection propre en GET pour éviter le message de ré-envoi de formulaire
    return RedirectResponse(url="/admin-dashboard?authorized=true", status_code=303)

@app.get("/admin-dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, authorized: Optional[str] = None, db: Session = Depends(get_db)):
    if authorized != "true":
        return RedirectResponse(url="/admin-login", status_code=303)
    
    utilisateurs = db.query(UserDB).all()
    commercants = [u for u in utilisateurs if u.role == "commercant"]
    prestataires = [u for u in utilisateurs if u.role == "prestataire"]
    
    total_users = len(commercants) + len(prestataires)
    chiffre_affaires = total_users * 45000

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "total_commercants": len(commercants),
            "total_prestataires": len(prestataires),
            "chiffre_affaires": chiffre_affaires,
            "commercants": commercants,
            "prestataires": prestataires
        }
    )

