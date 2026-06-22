from web3.auto import w3
from eth_account.messages import encode_defunct
import sys


passwd = ''
msg = ''
cantidad_de_args = len(sys.argv)
if cantidad_de_args < 2 or cantidad_de_args > 3:
    print('Uso: python sign.py ruta_al_archivo_de_la_clave_privada [password]')
    exit(1)
else:
    if cantidad_de_args == 3:
        passwd = sys.argv[2]
    with open(sys.argv[1]) as keyfile:
        encrypted_key = keyfile.read()
        private_key = w3.eth.account.decrypt(encrypted_key, passwd)
        message = encode_defunct(text=msg)
        signed_message = w3.eth.account.sign_message(message, private_key = private_key)
        print(signed_message)
    exit(0)