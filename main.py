from enum import Enum
from typing import List, Optional
from datetime import datetime
import hashlib
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import JWTError, jwt

# --------------------------------------------------------------------------
# CONFIGURATION ET BASE DE DONNÉES (VERSION NATIONALE & BASSAM)
# --------------------------------------------------------------------------
DATABASE_URL = "sqlite:///./pme_marketplace.db"
SECRET_KEY = "cle_secrete_pme_ci_national_admin"
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed_password

# --------------------------------------------------------------------------
# ENUMS (Rôles & Statuts)
# --------------------------------------------------------------------------
class RoleEnum(str, Enum):
    commercant = "commercant"
    prestataire = "prestataire"
    admin = "admin"

class StatutDemandeEnum(str, Enum):
    en_attente = "en_attente"
    acceptee = "acceptee"
    terminee = "terminee"
    annulee = "annulee"

# --------------------------------------------------------------------------
# MODÈLES SQLALCHEMY (Flexible pour toute la Côte d'Ivoire)
# --------------------------------------------------------------------------
class UserDB(Base):
    __tablename__ = "utilisateurs"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default=RoleEnum.commercant.value)
    
    quartier = Column(String, nullable=True, default="Grand-Bassam") # Accepte n'importe quelle ville/commune (ex: Abidjan - Cocody)
    competence = Column(String, nullable=True)
    mobile_money_numero = Column(String, nullable=True)  # Numéro Mobile Money pour les 90%
    note_moyenne = Column(Float, default=0.0)
    disponible = Column(String, default="oui")

class DemandeDB(Base):
    __tablename__ = "demandes"
    id = Column(Integer, primary_key=True, index=True)
    commercant_id = Column(Integer, ForeignKey("utilisateurs.id"))
    prestataire_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=True)
    quartier = Column(String)  # Ville ou Quartier de la prestation
    service_cherche = Column(String)
    description = Column(String)
    statut = Column(String, default=StatutDemandeEnum.en_attente.value)
    prix_propose = Column(Float, default=0.0)

class TransactionDB(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    demande_id = Column(Integer, ForeignKey("demandes.id"))
    prestataire_id = Column(Integer, ForeignKey("utilisateurs.id"))
    montant_total = Column(Float)
    commission_plateforme = Column(Float)  # Vos 10% de fondateur
    montant_prestataire = Column(Float)    # Les 90% pour l'artisan
    moyen_paiement = Column(String)        # Wave, Orange Money, MTN
    numero_versement_artisan = Column(String)
    date_paiement = Column(DateTime, default=datetime.utcnow)

class AvisDB(Base):
    __tablename__ = "avis"
    id = Column(Integer, primary_key=True, index=True)
    prestataire_id = Column(Integer, ForeignKey("utilisateurs.id"))
    note = Column(Integer)
    commentaire = Column(String)

Base.metadata.create_all(bind=engine)

# --------------------------------------------------------------------------
# SCHÉMAS PYDANTIC
# --------------------------------------------------------------------------
class UserCreate(BaseModel):
    nom: str
    email: str
    password: str
    role: RoleEnum
    quartier: Optional[str] = "Grand-Bassam"
    competence: Optional[str] = None
    mobile_money_numero: Optional[str] = None

class UserOut(BaseModel):
    id: int
    nom: str
    email: str
    role: str
    quartier: Optional[str]
    competence: Optional[str]
    mobile_money_numero: Optional[str]
    note_moyenne: Optional[float]
    class Config:
        from_attributes = True

class DemandeCreate(BaseModel):
    quartier: str  # Ex: "Grand-Bassam", "Abidjan - Cocody", etc.
    service_cherche: str
    description: str
    prix_propose: float

class DemandeOut(BaseModel):
    id: int
    commercant_id: int
    prestataire_id: Optional[int]
    quartier: str
    service_cherche: str
    description: str
    statut: str
    prix_propose: float
    class Config:
        from_attributes = True

class PaiementCreate(BaseModel):
    demande_id: int
    moyen_paiement: str

class AvisCreate(BaseModel):
    note: int
    commentaire: str

# --------------------------------------------------------------------------
# UTILS & DÉPENDANCES
# --------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserDB:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token invalide")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = db.query(UserDB).filter(UserDB.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

app = FastAPI(title="PME Marketplace Côte d'Ivoire - National Pro")

@app.get("/")
def accueil():
    return {"message": "Bienvenue sur l'API PME Marketplace Côte d'Ivoire (Bassam & National)"}

# --------------------------------------------------------------------------
# ROUTES : AUTHENTIFICATION & UTILISATEURS
# --------------------------------------------------------------------------
@app.post("/utilisateurs/", response_model=UserOut)
def inscrire_utilisateur(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    nouvel_user = UserDB(
        nom=user.nom,
        email=user.email,
        hashed_password=hash_password(user.password),
        role=user.role.value,
        quartier=user.quartier,
        competence=user.competence,
        mobile_money_numero=user.mobile_money_numero
    )
    db.add(nouvel_user)
    db.commit()
    db.refresh(nouvel_user)
    return nouvel_user

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Identifiants incorrects")
    
    token = jwt.encode({"sub": user.email, "role": user.role}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

# --------------------------------------------------------------------------
# ROUTE : RECHERCHE GÉOGRAPHIQUE MULTI-VILLE (Bassam, Abidjan, etc.)
# --------------------------------------------------------------------------
@app.get("/prestataires", response_model=List[UserOut])
def rechercher_prestataires(
    quartier: Optional[str] = None, # Permet de chercher par ville ou commune (ex: Abidjan)
    competence: Optional[str] = None,
    note_min: Optional[float] = None,
    db: Session = Depends(get_db)
):
    query = db.query(UserDB).filter(UserDB.role == RoleEnum.prestataire.value)
    if quartier:
        query = query.filter(UserDB.quartier.ilike(f"%{quartier}%"))
    if competence:
        query = query.filter(UserDB.competence.ilike(f"%{competence}%"))
    if note_min is not None:
        query = query.filter(UserDB.note_moyenne >= note_min)
    return query.all()

# --------------------------------------------------------------------------
# ROUTE : WORKFLOW DES DEMANDES
# --------------------------------------------------------------------------
@app.post("/demandes/", response_model=DemandeOut)
def creer_demande(
    demande: DemandeCreate, 
    user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if user.role != RoleEnum.commercant.value:
        raise HTTPException(status_code=403, detail="Seuls les commerçants peuvent créer des demandes")
    
    nouvelle_demande = DemandeDB(
        commercant_id=user.id,
        quartier=demande.quartier,
        service_cherche=demande.service_cherche,
        description=demande.description,
        prix_propose=demande.prix_propose,
        statut=StatutDemandeEnum.en_attente.value
    )
    db.add(nouvelle_demande)
    db.commit()
    db.refresh(nouvelle_demande)
    return nouvelle_demande

@app.patch("/demandes/{demande_id}/statut", response_model=DemandeOut)
def changer_statut_demande(
    demande_id: int, 
    nouveau_statut: StatutDemandeEnum, 
    user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    demande = db.query(DemandeDB).filter(DemandeDB.id == demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande introuvable")

    if nouveau_statut == StatutDemandeEnum.acceptee:
        if user.role != RoleEnum.prestataire.value:
            raise HTTPException(status_code=403, detail="Seul un prestataire peut accepter un chantier")
        demande.prestataire_id = user.id

    demande.statut = nouveau_statut.value
    db.commit()
    db.refresh(demande)
    return demande

# --------------------------------------------------------------------------
# ROUTE : PAIEMENT MOBILE MONEY & REVERSEMENT (10% ADMIN / 90% ARTISAN)
# --------------------------------------------------------------------------
@app.post("/paiements/simuler")
def payer_prestation(
    paiement: PaiementCreate, 
    user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    demande = db.query(DemandeDB).filter(DemandeDB.id == paiement.demande_id).first()
    if not demande:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    
    if not demande.prestataire_id:
        raise HTTPException(status_code=400, detail="Aucun prestataire n'a accepté cette demande")

    prestataire = db.query(UserDB).filter(UserDB.id == demande.prestataire_id).first()
    numero_versement = prestataire.mobile_money_numero if prestataire and prestataire.mobile_money_numero else "Non renseigné"

    montant_total = demande.prix_propose
    commission_admin = montant_total * 0.10  # 10% pour vous (fondateur)
    montant_prestataire = montant_total * 0.90  # 90% pour l'artisan

    nouvelle_transac = TransactionDB(
        demande_id=demande.id,
        prestataire_id=prestataire.id,
        montant_total=montant_total,
        commission_plateforme=commission_admin,
        montant_prestataire=montant_prestataire,
        moyen_paiement=paiement.moyen_paiement,
        numero_versement_artisan=numero_versement
    )
    db.add(nouvelle_transac)
    demande.statut = StatutDemandeEnum.terminee.value
    db.commit()

    return {
        "message": f"Paiement validé avec succès via {paiement.moyen_paiement}",
        "montant_total": f"{montant_total} FCFA",
        "commission_fondateur_10_percent": f"{commission_admin} FCFA (Conservé par la plateforme)",
        "versement_artisan_90_percent": f"{montant_prestataire} FCFA (Transféré au {numero_versement})",
        "statut_demande": "terminee"
    }

# --------------------------------------------------------------------------
# ROUTES : TABLEAUX DE BORD (DASHBOARDS)
# --------------------------------------------------------------------------
@app.get("/dashboard/commercant")
def dashboard_commercant(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != RoleEnum.commercant.value:
        raise HTTPException(status_code=403, detail="Accès réservé aux commerçants")
    demandes = db.query(DemandeDB).filter(DemandeDB.commercant_id == user.id).all()
    return {"commercant": user.nom, "zone": user.quartier, "vos_demandes": demandes}

@app.get("/dashboard/prestataire")
def dashboard_prestataire(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != RoleEnum.prestataire.value:
        raise HTTPException(status_code=403, detail="Accès réservé aux prestataires")
    
    missions = db.query(DemandeDB).filter(DemandeDB.prestataire_id == user.id).all()
    reversements = db.query(TransactionDB).filter(TransactionDB.prestataire_id == user.id).all()
    
    return {
        "prestataire": user.nom,
        "zone_intervention": user.quartier,
        "numero_mobile_money": user.mobile_money_numero,
        "note_moyenne": user.note_moyenne,
        "missions": missions,
        "historique_gains_90_percent": reversements
    }

@app.get("/dashboard/admin")
def dashboard_fondateur(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)):
    total_users = db.query(UserDB).count()
    transactions = db.query(TransactionDB).all()
    gains_totaux_admin = sum([t.commission_plateforme for t in transactions])
    volume_global = sum([t.montant_total for t in transactions])
    
    return {
        "statut": "Vue Administrateur / Fondateur - Côte d'Ivoire (National)",
        "nombre_utilisateurs_total": total_users,
        "volume_affaires_global": f"{volume_global} FCFA",
        "chiffre_affaires_commissions_10_percent": f"{gains_totaux_admin} FCFA",
        "historique_global_transactions": transactions
    }

# --------------------------------------------------------------------------
# ROUTE : AVIS & NOTATION
# --------------------------------------------------------------------------
@app.post("/prestataires/{prestataire_id}/avis")
def laisser_avis(
    prestataire_id: int, 
    avis: AvisCreate, 
    user: UserDB = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    nouveau_avis = AvisDB(prestataire_id=prestataire_id, note=avis.note, commentaire=avis.commentaire)
    db.add(nouveau_avis)
    db.commit()

    tous_les_avis = db.query(AvisDB).filter(AvisDB.prestataire_id == prestataire_id).all()
    moyenne = sum([a.note for a in tous_les_avis]) / len(tous_les_avis)

    prestataire = db.query(UserDB).filter(UserDB.id == prestataire_id).first()
    if prestataire:
        prestataire.note_moyenne = round(moyenne, 2)
        db.commit()

    return {"message": "Avis pris en compte", "nouvelle_note_moyenne": prestataire.note_moyenne}

