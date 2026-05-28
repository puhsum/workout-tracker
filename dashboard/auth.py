import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "change-me")
ALGORITHM = "HS256"
EXPIRE_DAYS = 7


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
