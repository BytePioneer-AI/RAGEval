import base64
import binascii
import hashlib
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

NONCE_SIZE = 12
KEY_SIZE = 32


def _decode_master_key(value: str) -> bytes:
    if not value:
        raise ValueError("API_KEY_MASTER_KEY is not set")

    raw = value.strip()
    if len(raw) == 64:
        try:
            decoded = bytes.fromhex(raw)
            if len(decoded) == KEY_SIZE:
                return decoded
        except ValueError:
            pass

    try:
        padded = raw + "=" * (-len(raw) % 4)
        decoded = base64.urlsafe_b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("API_KEY_MASTER_KEY must be base64 or 32-byte hex") from exc

    if len(decoded) != KEY_SIZE:
        raise ValueError("API_KEY_MASTER_KEY must decode to 32 bytes")

    return decoded


def _get_master_key() -> bytes:
    return _decode_master_key(settings.API_KEY_MASTER_KEY or "")


def encrypt_api_key(plaintext: str) -> str:
    key = _get_master_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_api_key(payload: str) -> str:
    key = _get_master_key()
    padded = payload + "=" * (-len(payload) % 4)
    data = base64.urlsafe_b64decode(padded.encode("ascii"))
    if len(data) <= NONCE_SIZE:
        raise ValueError("Encrypted payload is invalid")
    nonce = data[:NONCE_SIZE]
    ciphertext = data[NONCE_SIZE:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def hash_api_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def get_key_last4(plaintext: str) -> str:
    return plaintext[-4:] if plaintext else ""
