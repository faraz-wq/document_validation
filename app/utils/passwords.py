"""
Password utilities using bcrypt for hashing and verification
"""

from passlib.context import CryptContext

# Initialize password hashing context
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(plain_password: str) -> str:
    """
    Generate a hash for a plain password
    """
    return pwd_context.hash(plain_password)