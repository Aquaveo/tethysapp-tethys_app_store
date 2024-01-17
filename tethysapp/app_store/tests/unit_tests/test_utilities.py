from tethysapp.app_store.utilities import encrypt, decrypt
from cryptography.fernet import Fernet


def test_encrypt():
    key = Fernet.generate_key().decode()
    password = "my password"

    encrypted_pass = encrypt(password, key)
    decrypted_pass = decrypt(encrypted_pass, key)

    assert decrypted_pass == password
