# Collez le code ci-dessus, sauvegardez (Ctrl+O, Entrée, Ctrl+X)
PYTHONPATH=. pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_accueil():
    response = client.get("/")
    assert response.status_code == 200
    assert "Bienvenue" in response.json()["message"]

def test_flux_complet_marketplace():
    # 1. Inscription d'un commerçant
    commercant_data = {
        "nom": "Boutique Bassam",
        "email": "commercant@bassam.ci",
        "password": "password123",
        "role": "commercant",
        "quartier": "Grand-Bassam"
    }
    client.post("/utilisateurs/", json=commercant_data)

    # 2. Inscription d'un prestataire
    prestataire_data = {
        "nom": "Aka Plomberie",
        "email": "prestataire@bassam.ci",
        "password": "password123",
        "role": "prestataire",
        "quartier": "Grand-Bassam",
        "competence": "Plomberie"
    }
    client.post("/utilisateurs/", json=prestataire_data)

    # 3. Connexion du commerçant pour récupérer le token JWT
    response_token = client.post("/token", data={"username": "commercant@bassam.ci", "password": "password123"})
    assert response_token.status_code == 200
    token_commercant = response_token.json()["access_token"]
    headers_commercant = {"Authorization": f"Bearer {token_commercant}"}

    # 4. Création d'une demande par le commerçant
    demande_data = {
        "quartier": "Grand-Bassam",
        "service_cherche": "Plomberie",
        "description": "Fuite d'eau urgente dans la boutique",
        "prix_propose": 25000.0
    }
    response_demande = client.post("/demandes/", json=demande_data, headers=headers_commercant)
    assert response_demande.status_code == 200
    demande_id = response_demande.json()["id"]

    # 5. Test du filtrage avancé des prestataires
    response_search = client.get("/prestataires?quartier=Grand-Bassam&competence=Plomberie")
    assert response_search.status_code == 200
    assert len(response_search.json()) > 0

    # 6. Connexion du prestataire pour accepter la demande
    token_prestataire = client.post("/token", data={"username": "prestataire@bassam.ci", "password": "password123"}).json()["access_token"]
    headers_prestataire = {"Authorization": f"Bearer {token_prestataire}"}

    response_status = client.patch(f"/demandes/{demande_id}/statut?nouveau_statut=acceptee", headers=headers_prestataire)
    assert response_status.status_code == 200
    assert response_status.json()["statut"] == "acceptee"

    # 7. Simulation du paiement Mobile Money (Wave / Orange Money) et calcul des 10%
    paiement_data = {
        "demande_id": demande_id,
        "moyen_paiement": "Wave"
    }
    response_paiement = client.post("/paiements/simuler", json=paiement_data, headers=headers_prestataire)
    assert response_paiement.status_code == 200
    data_paiement = response_paiement.json()
    assert "10%" in data_paiement["commission_plateforme_retenue"]
    assert data_paiement["statut_demande"] == "terminee"

