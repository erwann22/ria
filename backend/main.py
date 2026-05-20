# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import os

app = FastAPI()

# Configuration des variables d'environnement Google (à récupérer sur la console Google Cloud)
CLIENT_CREDS_FILE = "client_secret.json" 
# Définir les accès dont Ria a besoin (Mails, Agenda, Profil)
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

@app.get("/login")
def login():
    # Initialisation du flux d'authentification Google
    flow = Flow.from_client_secrets_file(
        CLIENT_CREDS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
def auth_callback(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_CREDS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/auth/callback"
    )
    flow.fetch_token(code=code)
    
    credentials = flow.credentials
    # ICI : On stocke les credentials de manière sécurisée (Session ou DB) pour cet utilisateur
    # credentials.token, credentials.refresh_token, etc.
    
    # Redirection vers notre page blanche HTML une fois connecté
    return RedirectResponse(url="http://localhost:5500/index.html?status=connected")