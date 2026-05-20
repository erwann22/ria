import os
import json
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

app = FastAPI(title="Ria API Backend")

# 1. Configuration CORS (crucial pour le lien Front/Back)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production (ex: ["http://localhost:5500"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration de l'environnement pour le développement local (permet le HTTP)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

CLIENT_CREDS_FILE = "client_secret_1008918750567-58cas4v87v43ua9lskp244rf1o5kgd0p.apps.googleusercontent.com.json"
# Les autorisations que Ria demande à l'utilisateur
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]
REDIRECT_URI = "http://localhost:8000/auth/callback"

# Simulation d'une base de données en mémoire pour le développement
# En production, on liera l'ID utilisateur à son refresh_token en BDD
USER_SESSION = {}

@app.get("/login")
def login():
    """Redirige l'utilisateur vers la page de connexion Google"""
    if not os.path.exists(CLIENT_CREDS_FILE):
        raise HTTPException(status_code=500, detail="Fichier client_secret.json manquant au niveau de la racine.")
        
    flow = Flow.from_client_secrets_file(
        CLIENT_CREDS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    # prompt='select_account' permet de changer de compte facilement au clic
    authorization_url, state = flow.authorization_url(
        access_type='offline', 
        include_granted_scopes='true',
        prompt='select_account'
    )
    return RedirectResponse(authorization_url)

@app.get("/auth/callback")
def auth_callback(code: str):
    """Reçoit le code de validation de Google et l'échange contre des jetons d'accès"""
    flow = Flow.from_client_secrets_file(
        CLIENT_CREDS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    # Extraction des infos utilisateur
    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info.get('email')

    # Sauvegarde des credentials pour Ria
    USER_SESSION[user_email] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    # Redirection vers ton interface Web (on passe l'email en paramètre pour la démo)
    return RedirectResponse(url=f"http://https://erwann22.github.io/ria/frontend/index.html?user={user_email}")

@app.get("/api/init-dashboard")
def init_dashboard(user: str):
    """Exemple d'outil : Va chercher les données Google pour nourrir Ria"""
    if user not in USER_SESSION:
        return JSONResponse(status_code=401, content={"status": "unauthenticated"})
    
    # Reconstitution des privilèges d'accès
    creds = Credentials(**USER_SESSION[user])
    
    try:
        # 1. Récupération des 3 prochains événements de l'Agenda
        calendar_service = build('calendar', 'v3', credentials=creds)
        events_result = calendar_service.events().list(
            calendarId='primary', maxResults=3, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # 2. Récupération des 3 derniers emails non lus
        gmail_service = build('gmail', 'v1', credentials=creds)
        gmail_result = gmail_service.users().messages().list(
            userId='me', maxResults=3, q="is:unread"
        ).execute()
        messages = gmail_result.get('messages', [])
        
        # Structuration légère des données pour le test
        dashboard_data = {
            "status": "connected",
            "agenda": [{"title": e.get('summary'), "start": e.get('start').get('dateTime', e.get('start').get('date'))} for e in events],
            "mails_count": len(messages)
        }
        return dashboard_data

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)