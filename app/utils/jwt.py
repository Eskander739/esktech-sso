import json
import base64
import hmac
import hashlib
import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv


class JWTService:
    def __init__(self, algorithm: str = "HS256"):
        load_dotenv()
        self.secret_key = os.environ.get("SECRET_KEY")
        self.algorithm = algorithm

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        """Base64url encoding без padding"""
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _base64url_decode(data: str) -> bytes:
        """Base64url decoding с добавлением padding при необходимости"""
        padding = len(data) % 4
        if padding:
            data += "=" * (4 - padding)
        return base64.urlsafe_b64decode(data)

    def _sign(self, msg: bytes) -> str:
        """Создание подписи для JWT"""
        if self.algorithm == "HS256":
            signature = hmac.new(
                self.secret_key.encode("utf-8"), msg, hashlib.sha256
            ).digest()
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        return self._base64url_encode(signature)

    def encode(
        self,
        payload: dict,
        expires_delta: timedelta | None = timedelta(weeks=1),
    ) -> str:
        """
        Создание JWT токена
        :param payload: Данные для включения в токен
        :param expires_delta: Время жизни токена
        :return: JWT токен
        """
        payload = payload.copy()
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
            payload["exp"] = int(expire.timestamp())

        # Заголовок JWT
        header = {"alg": self.algorithm, "typ": "JWT"}

        # Кодирование частей токена
        header_encoded = self._base64url_encode(json.dumps(header).encode("utf-8"))
        payload_encoded = self._base64url_encode(json.dumps(payload).encode("utf-8"))

        # Создание подписи
        message = f"{header_encoded}.{payload_encoded}".encode("utf-8")
        signature = self._sign(message)

        return f"{header_encoded}.{payload_encoded}.{signature}"

    def decode(self, token: str) -> dict:
        """
        Проверка и декодирование JWT токена
        :param token: JWT токен
        :return: Декодированные данные
        :raises: ValueError если токен невалиден
        """
        try:
            header_encoded, payload_encoded, signature = token.split(".")
        except ValueError:
            raise ValueError("Invalid JWT format")

        # Проверка подписи
        message = f"{header_encoded}.{payload_encoded}".encode("utf-8")
        expected_signature = self._sign(message)
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("Invalid JWT signature")

        # Декодирование payload
        payload_json = self._base64url_decode(payload_encoded).decode("utf-8")
        payload = json.loads(payload_json)

        # Проверка срока действия
        if "exp" in payload:
            if datetime.now(UTC) > datetime.fromtimestamp(payload["exp"]):
                raise ValueError("Token expired")

        return payload

    def validate_token(self, token: str) -> bool:
        """Проверка валидности токена"""
        try:
            self.decode(token)
            return True
        except ValueError:
            return False


if __name__ == "__main__":
    jj = JWTService()
    print(
        jj.encode(
            {
                "email": "admin@example.com",
                "role": "admin",
            },
            timedelta(weeks=9999),
        )
    )
    a = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJlbWFpbCI6ICJ0ZXN0QGV4YW1wbGUuY29tIiwgInJvbGUiOiAiYWRtaW4iLCAiZXhwIjogNzgxODAxNTUxNH0.6Q4pOFrxgtIfgBEruaOw9ASI01Cq-D649fdBouprDkw"
    b = jj.decode(a)
    b.pop("exp")
    print(b)
    # print(jj.encode({"egceska@gmail.com": "1234"}))
    # print(jj.validate_token('eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJlZ2Nlc2thQGdtYWlsLmNvbSI6ICIxMjM0NTY3OCIsICJleHAiOiAxNzQzOTUzNDA0fQ.ybQZ7SDgcv2_NKwE1a6F1CrB7KfhlJepfu6M2UNorHY'))
