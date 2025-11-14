import io
import os
import time
import zipfile
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

APP_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.abspath(os.path.join(APP_DIR, ".."))
PKI_DIR = os.path.join(BASE_DIR, "pki")        # mounted volume: ./secrets/pki
MQTT_DIR = os.path.join(BASE_DIR, "mqtt")      # mounted volume: ./secrets/mqtt

DOMAIN = os.getenv("DOMAIN", "example.com")
CERT_MODE = os.getenv("CERT_MODE", "private")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
UI_ORIGIN = os.getenv("UI_ORIGIN")  # e.g., https://ui.example.com

app = FastAPI(title="AirVibe Edge API")

# CORS
allow_origins = ["*"] if not UI_ORIGIN else [UI_ORIGIN]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

def require_admin(auth: Optional[str]) -> None:
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN not configured")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth.split(" ", 1)[1]
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

def load_pem(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def write_bytes(path: str, data: bytes, mode: int = 0o640) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    os.chmod(path, mode)

def ensure_issuing_ca():
    """
    Ensure an Issuing CA (client-auth CA) exists in /app/pki:
      - issuing_ca.key (RSA)
      - issuing_ca.crt (self-signed CA:TRUE)
    """
    key_path = os.path.join(PKI_DIR, "issuing_ca.key")
    crt_path = os.path.join(PKI_DIR, "issuing_ca.crt")
    if os.path.exists(key_path) and os.path.exists(crt_path):
        return key_path, crt_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"AirVibe Issuing CA")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(days=1))
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(key_cert_sign=True, crl_sign=True, digital_signature=False,
                                     content_commitment=False, key_encipherment=False, data_encipherment=False,
                                     key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )
    write_bytes(key_path, key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ), 0o600)
    write_bytes(crt_path, cert.public_bytes(serialization.Encoding.PEM), 0o644)
    return key_path, crt_path

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/public/actility/fields")
def public_fields():
    return {
        "hostname": f"edge.{DOMAIN}:8883",
        "protocol": "SSL",
        "publish": "mqtt/things/{DevEUI}/uplink",
        "subscribe": "mqtt/things/{DevEUI}/downlink",
        "cert_mode": CERT_MODE,
        "server_ca_available": os.path.exists(os.path.join(PKI_DIR, "server_ca.crt")) or os.path.exists(os.path.join(MQTT_DIR, "server.crt")),
    }

@app.get("/admin/pki/server-ca")
def download_server_ca(authorization: Optional[str] = Header(None)):
    require_admin(authorization)
    # If CERT_MODE=private, we expose the private Server CA public cert
    server_ca = os.path.join(PKI_DIR, "server_ca.crt")
    if os.path.exists(server_ca):
        return FileResponse(server_ca, filename="server_ca.crt", media_type="application/x-pem-file")
    # If using LE, most connectors don't need a CA uploaded (trusted globally).
    # If Actility insists on a file, you may upload the LE chain; exposing it here is non-critical.
    le_chain = os.path.join(MQTT_DIR, "server.crt")  # fullchain; not strictly a CA, but may be accepted
    if os.path.exists(le_chain):
        return FileResponse(le_chain, filename="server_fullchain.crt", media_type="application/x-pem-file")
    raise HTTPException(status_code=404, detail="No server CA/chain available")

@app.post("/admin/pki/issue-connector")
def issue_connector(cn: Optional[str] = Query(default=None), authorization: Optional[str] = Header(None)):
    """
    Issues a client certificate + PKCS#8 key signed by Issuing CA.
    Returns a zip containing:
      - client.crt
      - client_pkcs8.key
      - ca.crt (Issuing CA public cert)
      - server_ca.crt (if CERT_MODE=private, Server CA public cert; else optional LE chain)
    """
    require_admin(authorization)
    ensure_issuing_ca()
    ca_key_p = os.path.join(PKI_DIR, "issuing_ca.key")
    ca_crt_p = os.path.join(PKI_DIR, "issuing_ca.crt")
    ca_key = serialization.load_pem_private_key(load_pem(ca_key_p), password=None)
    ca_cert = x509.load_pem_x509_certificate(load_pem(ca_crt_p))

    common_name = cn or f"actility-connector-{int(time.time())}"
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .sign(key, hashes.SHA256())
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(hours=1))
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=True,
                                     key_cert_sign=False, crl_sign=False, content_commitment=False,
                                     data_encipherment=False, key_agreement=False,
                                     encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )

    client_crt = cert.public_bytes(serialization.Encoding.PEM)
    client_pkcs8 = key.private_bytes(
        serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    issuing_ca_pem = load_pem(ca_crt_p)

    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("client.crt", client_crt)
        z.writestr("client_pkcs8.key", client_pkcs8)
        z.writestr("ca.crt", issuing_ca_pem)
        # Provide server CA/chain for Actility "CA Certificate" if using private mode
        if CERT_MODE == "private":
            server_ca = os.path.join(PKI_DIR, "server_ca.crt")
            if os.path.exists(server_ca):
                z.writestr("server_ca.crt", load_pem(server_ca))
        else:
            # Optional: expose LE fullchain if present
            le_chain = os.path.join(MQTT_DIR, "server.crt")
            if os.path.exists(le_chain):
                z.writestr("server_fullchain.crt", load_pem(le_chain))
    mem.seek(0)
    filename = f"connector-creds-{common_name}.zip"
    return StreamingResponse(mem, media_type="application/zip",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})
