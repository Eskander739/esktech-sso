from utils.password_validator import hash_password, verify_password


def test_hash_and_verify():
    pwd = "secret123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong", hashed) is False
