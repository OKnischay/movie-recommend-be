import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from users.models import CustomUser as User


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        header = request.headers.get('Authorization', None)

        if not header or not header.startswith("Bearer "):
            return None  # No token = no auth; let other auth backends try

        token = header.split(" ")[1]

        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

            if payload.get("type") != "access":
                raise exceptions.AuthenticationFailed("Token is not an access token")

            user = User.objects.get(id=payload["id"])

            if getattr(user, 'is_deleted', False):
                raise exceptions.AuthenticationFailed("Account has been deactivated")

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired")
        except jwt.DecodeError:
            raise exceptions.AuthenticationFailed("Invalid token")
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found")

        return (user, payload)
