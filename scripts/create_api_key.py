#!/usr/bin/env python3
"""
Generate Shareable API Authentication Keys (Bearer Tokens)
===========================================================
Generates signed cryptographic JWT tokens that you can share with colleagues,
external clients, or automated services to access your Nemotron Agent Engine.

Usage:
  python3 scripts/create_api_key.py --email alice@example.com --days 30 --role DEVELOPER
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.modules.auth.service import auth_service
from app.modules.auth.policy_engine import ROLE_PERMISSIONS


def generate_key(email: str, days: int, role: str, tenant: str = "default-tenant") -> str:
    lifetime_seconds = days * 86400 if days > 0 else 365 * 86400  # Default to 1 year if 0
    roles = [role.upper()]
    permissions = list(ROLE_PERMISSIONS.get(role.upper(), {"model.use", "repository.read"}))

    token = auth_service.create_access_token(
        user_id=email,
        session_id=f"apikey-{email}",
        tenant_id=tenant,
        roles=roles,
        scopes=permissions,
        lifetime_seconds=lifetime_seconds,
    )
    return token


def main():
    parser = argparse.ArgumentParser(
        description="Create a shareable API authentication key for Nemotron Agent Engine."
    )
    parser.add_argument(
        "--email",
        "-e",
        default="collaborator@example.com",
        help="Email or identifier of the person/service receiving the key.",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=30,
        help="Number of days the key will remain valid (e.g. 30, 90, 365). Default: 30 days.",
    )
    parser.add_argument(
        "--role",
        "-r",
        default="DEVELOPER",
        choices=["DEVELOPER", "PROJECT_ADMIN", "ORG_ADMIN", "SUPER_ADMIN"],
        help="Access role granted to this key. Default: DEVELOPER.",
    )
    parser.add_argument(
        "--tenant",
        "-t",
        default="default-tenant",
        help="Tenant / Organization ID. Default: default-tenant.",
    )

    args = parser.parse_args()

    token = generate_key(args.email, args.days, args.role, args.tenant)

    print("=" * 80)
    print("🔑 NEMOTRON AGENT ENGINE — SHAREABLE API AUTHENTICATION KEY")
    print("=" * 80)
    print(f"Recipient Identity : {args.email}")
    print(f"Granted Role       : {args.role}")
    print(f"Validity Period    : {args.days} days")
    print(f"Tenant ID          : {args.tenant}")
    print("-" * 80)
    print("SEND THIS BEARER TOKEN TO YOUR COLLABORATOR:")
    print()
    print(token)
    print()
    print("-" * 80)
    print("HOW THE RECIPIENT USES THIS KEY:")
    print()
    print("1. In cURL:")
    print(f'   curl -H "Authorization: Bearer {token}" http://<YOUR_SERVER_IP>:8000/api/v1/auth/me')
    print()
    print("2. In Python (requests / httpx):")
    print("   import requests")
    print(f'   headers = {{"Authorization": "Bearer {token}"}}')
    print('   resp = requests.get("http://<YOUR_SERVER_IP>:8000/api/v1/models", headers=headers)')
    print("   print(resp.json())")
    print()
    print("3. In Swagger UI / OpenAPI Docs:")
    print("   Navigate to http://<YOUR_SERVER_IP>:8000/docs")
    print("   Click the green [Authorize] button at the top-right.")
    print(f'   Enter: Bearer {token}')
    print("=" * 80)


if __name__ == "__main__":
    main()
