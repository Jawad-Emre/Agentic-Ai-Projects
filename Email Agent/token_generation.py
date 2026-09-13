# generate_token.py — run this locally, once
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

print("REFRESH TOKEN:", creds.refresh_token)
print("CLIENT ID:", creds.client_id)
print("CLIENT SECRET:", creds.client_secret)