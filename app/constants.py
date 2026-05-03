from enum import Enum

REDIS_POOL_SIZE = 10
DB_POOL_SIZE = 10
WS_POOL_SIZE = 10


class ApiVersion:
    V0 = "/api/v0"
    V1 = "/api/v1"
    V2 = "/api/v2"


PROD_ENV = "opt/fast-api-users.env"
CODE_EXPIRE_MINUTES = 5

class AccessTokenFormat(str, Enum):
    OPAQUE = "opaque" # возможность отзывать токены (JWT нельзя отозвать, он живёт, пока не истечёт)
    JWT = "jwt"

class GrantType(str, Enum):
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"
    AUTHORIZATION_CODE = "authorization_code"