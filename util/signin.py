from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii

def encrypt_password_for_signin(password, device_id):
    try:
        key_source = device_id.encode('utf-8')
        key = key_source[:32]
        iv = key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        password_bytes = password.encode('utf-8')
        padded_password = pad(password_bytes, AES.block_size, style='pkcs7')
        encrypted_data = cipher.encrypt(padded_password)
        encrypted_hex = binascii.hexlify(encrypted_data).decode('utf-8')
        return encrypted_hex
    except Exception as e:
        return f"An error occurred during encryption of the password: {e}"
