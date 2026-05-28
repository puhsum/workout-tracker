#!/usr/bin/env python3
"""Run once to generate credentials. Copy output into dashboard/.env"""
import secrets
import getpass
import bcrypt

password = getpass.getpass("Choose a dashboard password: ")
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
secret = secrets.token_hex(32)

print("\nAdd these lines to dashboard/.env:\n")
print(f"DASHBOARD_USERNAME=gabe")
print(f"DASHBOARD_PASSWORD_HASH={hashed}")
print(f"DASHBOARD_SECRET_KEY={secret}")
