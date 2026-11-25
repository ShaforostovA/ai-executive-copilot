import json

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr


class CredentialEncryptionError(Exception):
    pass


class CredentialCipher:
    def __init__(self, key: SecretStr | None) -> None:
        if key is None or not key.get_secret_value().strip():
            raise CredentialEncryptionError("COPILOT_CREDENTIAL_ENCRYPTION_KEY is required.")
        try:
            self._fernet = Fernet(key.get_secret_value().encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise CredentialEncryptionError("Credential encryption key is invalid.") from exc

    def encrypt_credentials(self, username: str, password: str) -> str:
        payload = json.dumps({"username": username, "password": password}).encode("utf-8")
        return self._fernet.encrypt(payload).decode("ascii")

    def decrypt_credentials(self, ciphertext: str) -> tuple[str, str]:
        try:
            payload = json.loads(self._fernet.decrypt(ciphertext.encode("ascii")))
            return str(payload["username"]), str(payload["password"])
        except (InvalidToken, ValueError, KeyError, TypeError) as exc:
            raise CredentialEncryptionError("Stored credentials cannot be decrypted.") from exc
