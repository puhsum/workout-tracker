#!/usr/bin/env python3
"""Run once to generate credentials. Copy output into dashboard/.env"""
import secrets
import getpass
from passlib.context import CryptContext

ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = getpass.getpass("Choose a dashboard password: ")
hashed = ctx.hash(password)
secret = secrets.token_hex(32)

print("\nAdd these lines to dashboard/.env:\n")
print(f"DASHBOARD_USERNAME=gabe")
print(f"DASHBOARD_PASSWORD_HASH={hashed}")
print(f"DASHBOARD_SECRET_KEY={secret}")
