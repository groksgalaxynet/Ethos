# x0vs_crypto_envelope.py — Pythonista 3, no extras
# Envelope: per-record DEK, per-wallet KEK (file keystore), AES-256-CTR + HMAC-SHA256, HKDF
import os, json, hmac, hashlib, base64
from ctypes import cdll, c_void_p, c_size_t, c_int, byref, create_string_buffer, c_char_p

# ---------- utils ----------
def b64e(b: bytes) -> str: return base64.b64encode(b).decode('ascii')
def b64d(s: str) -> bytes: return base64.b64decode(s.encode('ascii'))

def hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int) -> bytes:
    if not salt: salt = b'\x00' * hashlib.sha256().digest_size
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    out = b''; T = b''
    for i in range(1, (length + 31)//32 + 1):
        T = hmac.new(prk, T + info + bytes([i]), hashlib.sha256).digest()
        out += T
    return out[:length]

def hmac_sha256(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()

# ---------- CommonCrypto AES-CTR ----------
_cc = None
for path in ('/usr/lib/libCommonCrypto.dylib', '/usr/lib/system/libcommonCrypto.dylib'):
    try:
        _cc = cdll.LoadLibrary(path); break
    except OSError:
        pass
if _cc is None:
    raise RuntimeError('CommonCrypto not found')

kCCSuccess = 0
kCCEncrypt, kCCDecrypt = 0, 1
kCCAlgorithmAES = 0
kCCModeCTR = 7
CCCryptorRef = c_void_p

_cc.CCCryptorCreateWithMode.argtypes = [c_int, c_int, c_int, c_int,
                                        c_void_p, c_void_p, c_size_t,
                                        c_void_p, c_size_t, c_int, c_int,
                                        c_void_p]
_cc.CCCryptorCreateWithMode.restype = c_int
_cc.CCCryptorRelease.argtypes = [CCCryptorRef]; _cc.CCCryptorRelease.restype = c_int
_cc.CCCryptorUpdate.argtypes  = [CCCryptorRef, c_void_p, c_size_t, c_void_p, c_size_t, c_void_p]
_cc.CCCryptorUpdate.restype   = c_int
_cc.CCCryptorFinal.argtypes   = [CCCryptorRef, c_void_p, c_size_t, c_void_p]
_cc.CCCryptorFinal.restype    = c_int

def aes_ctr_crypt(key: bytes, iv16: bytes, data: bytes, op: int) -> bytes:
    if len(key) not in (16,24,32): raise ValueError('AES key must be 16/24/32 bytes')
    if len(iv16)!=16: raise ValueError('CTR IV must be 16 bytes')
    cryptor = CCCryptorRef()
    res = _cc.CCCryptorCreateWithMode(op, kCCModeCTR, kCCAlgorithmAES, 0,
                                      c_char_p(iv16), c_char_p(key), c_size_t(len(key)),
                                      None, 0, 0, 0, byref(cryptor))
    if res != kCCSuccess: raise RuntimeError('CCCryptorCreateWithMode failed: %d'%res)
    out = create_string_buffer(len(data))
    moved = c_size_t(0)
    res = _cc.CCCryptorUpdate(cryptor, c_char_p(data), c_size_t(len(data)), out, c_size_t(len(data)), byref(moved))
    if res != kCCSuccess:
        _cc.CCCryptorRelease(cryptor); raise RuntimeError('CCCryptorUpdate failed: %d'%res)
    moved2 = c_size_t(0)
    res = _cc.CCCryptorFinal(cryptor, None, c_size_t(0), byref(moved2))
    _cc.CCCryptorRelease(cryptor)
    if res != kCCSuccess: raise RuntimeError('CCCryptorFinal failed: %d'%res)
    return out.raw[:moved.value]

def aead_encrypt_ctr_hmac(master_key: bytes, plaintext: bytes, aad: bytes=b'') -> dict:
    k = hkdf_sha256(master_key, b'', b'x0vs|content|kdf', 64)
    enc_key, mac_key = k[:32], k[32:]
    iv = os.urandom(16)
    ct = aes_ctr_crypt(enc_key, iv, plaintext, kCCEncrypt)
    tag = hmac_sha256(mac_key, iv + aad + ct)
    return {'alg':'AES-256-CTR+HMAC-SHA256','iv':b64e(iv),'ct':b64e(ct),'tag':b64e(tag)}

def aead_decrypt_ctr_hmac(master_key: bytes, enc: dict, aad: bytes=b'') -> bytes:
    k = hkdf_sha256(master_key, b'', b'x0vs|content|kdf', 64)
    enc_key, mac_key = k[:32], k[32:]
    iv, ct, tag = b64d(enc['iv']), b64d(enc['ct']), b64d(enc['tag'])
    calc = hmac_sha256(mac_key, iv + aad + ct)
    if not hmac.compare_digest(calc, tag): raise ValueError('HMAC verification failed')
    return aes_ctr_crypt(enc_key, iv, ct, kCCDecrypt)

# ---------- simple file keystore for KEKs ----------
KEK_STORE = os.path.expanduser('~/Documents/x0vs_kek_store.json')

def _load_store():
    if not os.path.exists(KEK_STORE): return {}
    try:
        with open(KEK_STORE,'r') as f: return json.load(f)
    except Exception: return {}

def _save_store(d):
    tmp = KEK_STORE + '.tmp'
    with open(tmp,'w') as f: json.dump(d,f,sort_keys=True,separators=(',',':'))
    os.replace(tmp, KEK_STORE)

def ensure_wallet(wallet_id: str) -> bytes:
    d = _load_store()
    b64 = d.get(wallet_id)
    if b64:
        return base64.b64decode(b64.encode('ascii'))
    kek = os.urandom(32)
    d[wallet_id] = b64e(kek)
    _save_store(d)
    return kek

# ---------- wrap/unwrap DEK with KEK ----------
def wrap_dek_for_wallet(wallet_id: str, dek: bytes) -> dict:
    kek = ensure_wallet(wallet_id)
    sub = hkdf_sha256(kek, b'', b'x0vs|wrap|kdf', 64)
    enc_key, mac_key = sub[:32], sub[32:]
    iv = os.urandom(16)
    ct = aes_ctr_crypt(enc_key, iv, dek, kCCEncrypt)
    tag = hmac_sha256(mac_key, iv + ct)
    return {'alg':'KEK:AES-256-CTR+HMAC-SHA256','iv':b64e(iv),'ct':b64e(ct),'tag':b64e(tag)}

def unwrap_dek_with_wallet(wallet_id: str, wrap: dict) -> bytes:
    kek = ensure_wallet(wallet_id)
    sub = hkdf_sha256(kek, b'', b'x0vs|wrap|kdf', 64)
    enc_key, mac_key = sub[:32], sub[32:]
    iv, ct, tag = b64d(wrap['iv']), b64d(wrap['ct']), b64d(wrap['tag'])
    calc = hmac_sha256(mac_key, iv + ct)
    if not hmac.compare_digest(calc, tag): raise ValueError('wrap HMAC failed')
    return aes_ctr_crypt(enc_key, iv, ct, kCCDecrypt)

# ---------- record API ----------
def encrypt_for_wallets(plaintext: bytes, wallet_ids: list, aad: bytes=b'') -> dict:
    dek = os.urandom(32)
    enc = aead_encrypt_ctr_hmac(dek, plaintext, aad=aad)
    wrapped = {f'wallet:{wid}': wrap_dek_for_wallet(wid, dek) for wid in wallet_ids}
    return {'ver':1,'cipher':enc['alg'],'iv':enc['iv'],'ct':enc['ct'],'tag':enc['tag'],
            'wrapped':wrapped,'kdf':'HKDF-SHA256','notes':'envelope: DEK per-record, KEK per-wallet'}

def decrypt_with_wallet(envelope: dict, wallet_id: str, aad: bytes=b'') -> bytes:
    w = envelope['wrapped'].get(f'wallet:{wallet_id}')
    if not w: raise KeyError('wallet not authorized')
    dek = unwrap_dek_with_wallet(wallet_id, w)
    enc = {'alg':envelope['cipher'],'iv':envelope['iv'],'ct':envelope['ct'],'tag':envelope['tag']}
    return aead_decrypt_ctr_hmac(dek, enc, aad=aad)

def envelope_json(envelope: dict) -> str:
    return json.dumps(envelope, sort_keys=True, separators=(',',':'))

def envelope_from_json(s: str) -> dict:
    return json.loads(s)
