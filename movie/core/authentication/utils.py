# users/utils/tokens.py
import jwt
from django.utils import timezone
from core import settings
from users.models import CustomUser as User

def generate_access_token(user: User):
    payload = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": timezone.now(),
        "exp": timezone.now() + timezone.timedelta(minutes=5),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def generate_refresh_token(user: User):
    payload = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "iat": timezone.now(),
        "exp": timezone.now() + timezone.timedelta(days=1),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def get_tokens(user: User):
    return [generate_access_token(user), generate_refresh_token(user)]

def decode_jwt_token(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
