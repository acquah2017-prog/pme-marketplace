import hashlib
from enum import Enum
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./pme_marketplace.db"
SECRET_KEY = "cle_secrete_pme_ci_national_admin"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)
    metier = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PME Marketplace Côte d'Ivoire")
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
def register_user(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    metier: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Cet email est déjà utilisé."}
        )
    
    hashed_pwd = hash_password(password)
    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=hashed_pwd,
        role=role,
        metier=metier
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url=f"/dashboard?email={new_user.email}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    hashed_pwd = hash_password(password)
    user = db.query(User).filter(User.email == email, User.password_hash == hashed_pwd).first()
    
    if not user:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Email ou mot de passe incorrect."}
        )
    
    return RedirectResponse(url=f"/dashboard?email={user.email}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/login-admin", response_class=HTMLResponse)
def login_admin_page(request: Request):
    return templates.TemplateResponse("login_admin.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, email: Optional[str] = None, db: Session = Depends(get_db)):
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "user": user}
    )

