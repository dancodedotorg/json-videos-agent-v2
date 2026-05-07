"""Google service account authentication utilities."""

import base64
import json
import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession

# Resolve repo root from __file__ location (cwd-independent)
# lib/google_auth.py -> scripts/lib -> scripts -> lesson-ground -> skills -> .claude -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
load_dotenv(_REPO_ROOT / "generation" / "tools" / ".env")

SLIDES_SCOPES = [
    "https://www.googleapis.com/auth/presentations.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_service_account_creds_from_env(
    env_var: str = "GOOGLE_SERVICE_ACCOUNT_JSON",
    scopes: List[str] = SLIDES_SCOPES,
) -> Credentials:
    raw = os.environ.get(env_var)
    if not raw:
        raise ValueError(
            f"Missing env var {env_var}. Add base64-encoded service account JSON to generation/tools/.env."
        )
    decoded = base64.b64decode(raw).decode("utf-8")
    info = json.loads(decoded)
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


def _build_slides_service(creds: Credentials):
    return build("slides", "v1", credentials=creds, cache_discovery=False)


def _build_authed_session(creds: Credentials) -> AuthorizedSession:
    return AuthorizedSession(creds)
