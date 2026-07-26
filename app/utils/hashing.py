import hashlib

def hash_content(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()