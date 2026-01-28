import os
import json
import base64
import datetime
import mimetypes
import requests
from typing import Optional
from urllib.parse import quote
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

OCI_ENVIRONMENTS = {
    "DEV": {
        "USER_OCID": "ocid1.user.oc1..aaaaaaaalh4xcdrgxk4b5qisawhtffgrjblonsbw3ddbidhtal6crkx74deq",
        "FINGERPRINT": "ea:bb:15:fd:8b:11:a4:1d:d7:28:e0:90:3c:60:50:ff",
        "PRIVATE_KEY_PATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "keys", "private-user-infra-ddw3-dev.pem")),
    },
    "PRD": {
        "USER_OCID": "ocid1.user.oc1..aaaaaaaalxuonbpzzykeam2ixit4kycr6wokpijqtq2g24pit64ik2cqwxia",
        "FINGERPRINT": "fa:93:19:ea:0b:0d:58:ab:3a:77:88:1c:c3:ca:c3:49",
        "PRIVATE_KEY_PATH": os.path.abspath(os.path.join(os.path.dirname(__file__), "keys", "private-user-infra-ddw3-prd.pem")),
    }
}
TENANCY_OCID = "ocid1.tenancy.oc1..aaaaaaaand4xcanpaqckfaohjrk66dccmt65my7m7ckz5p3n2hf5ccza6skq"

REGION = "sa-saopaulo-1"
TENANCY_OCID     = os.getenv("TENANCY_OCID", TENANCY_OCID)
USER_OCID        = None
FINGERPRINT      = None
_DEFAULT_PRIVATE_KEY_PATH = os.path.expanduser("~/.oci/key_cli_oci.pem")
PRIVATE_KEY_PATH = _DEFAULT_PRIVATE_KEY_PATH
REGION           = os.getenv("REGION", REGION)
COMPARTMENT_OCID = os.getenv("COMPARTMENT_OCID")
HOST = f"objectstorage.{REGION}.oraclecloud.com"
NAMESPACE = "grwpg6hbkpoi"
# ====== CHAVE ======
def load_private_key():

    b64 = os.getenv("OCI_PRIVATE_KEY_B64")
    pem = os.getenv("OCI_PRIVATE_KEY_PEM")
    # Prioriza PRIVATE_KEY_PATH global (definido por apply_oci_environment) sobre variável de ambiente
    # Se PRIVATE_KEY_PATH foi modificado do valor padrão, usa ele; senão, usa variável de ambiente se disponível
    if PRIVATE_KEY_PATH != _DEFAULT_PRIVATE_KEY_PATH:
        path = PRIVATE_KEY_PATH
    else:
        path = os.getenv("OCI_PRIVATE_KEY_PATH", PRIVATE_KEY_PATH)

    try:
        if b64:
            print(f"🔑 Carregando chave de OCI_PRIVATE_KEY_B64 (env var)")
            pem_bytes = base64.b64decode(b64.strip())
            return serialization.load_pem_private_key(pem_bytes, password=None)

        if pem:
            print(f"🔑 Carregando chave de OCI_PRIVATE_KEY_PEM (env var)")
            pem_bytes = pem.replace("\\n", "\n").strip().encode("utf-8")
            return serialization.load_pem_private_key(pem_bytes, password=None)

        print(f"🔑 Carregando chave do arquivo: {path}")
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    except FileNotFoundError as e:
        raise RuntimeError(f"Chave não encontrada em '{path}'. "
                           "Defina OCI_PRIVATE_KEY_B64 ou OCI_PRIVATE_KEY_PEM.") from e
    except (ValueError, TypeError) as e:
        raise RuntimeError(
            "Falha ao carregar a chave privada OCI. "
            "Confirme se é um PEM válido com delimiters "
            "-----BEGIN PRIVATE KEY----- / -----END PRIVATE KEY----- "
            "ou forneça OCI_PRIVATE_KEY_B64 corretamente."
        ) from e
def sign_request(private_key, signing_string):
    signature = private_key.sign(
        signing_string.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")


# ====== NAMESPACE ======
def get_namespace():
    global NAMESPACE
    if NAMESPACE:
        return NAMESPACE

    print("🔍 Buscando namespace...")

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = "/n/"

    signing_string = f"(request-target): get {request_target}\ndate: {now}\nhost: {HOST}"
    signature = sign_request(private_key, signing_string)

    authorization = (
        f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
        f'algorithm="rsa-sha256",headers="(request-target) date host",signature="{signature}"'
    )

    headers = {
        "Date": now,
        "Host": HOST,
        "Authorization": authorization
    }

    try:
        response = requests.get(f"https://{HOST}{request_target}", headers=headers)
        response.raise_for_status()
        NAMESPACE = response.text.strip('"')  # remove aspas da resposta
        print(f"✅ Namespace encontrado: {NAMESPACE}")
        return NAMESPACE

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao obter namespace: {e}")
        return None


    ###

def resolve_environment_from_compartment_name(name: str) -> str:
    lname = name.lower()

    if lname.endswith("-dev"):
        return "DEV"
    if lname.endswith("-prd"):
        return "PRD"

    raise ValueError(f"Não foi possível determinar ambiente do compartment '{name}'")

def apply_oci_environment(env: str):
    global USER_OCID, FINGERPRINT, PRIVATE_KEY_PATH

    cfg = OCI_ENVIRONMENTS[env]

    USER_OCID = cfg["USER_OCID"]
    FINGERPRINT = cfg["FINGERPRINT"]
    PRIVATE_KEY_PATH = cfg["PRIVATE_KEY_PATH"]
###
def _is_ocid_compartment(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.startswith("ocid1.compartment")

def resolve_compartment_ocid(name: str) -> Optional[str]:
    if not name:
        return None

    # 🔥 1) DESCOBRE O AMBIENTE PELO NOME (ANTES DE TUDO)
    env = resolve_environment_from_compartment_name(name)

    # 🔥 2) APLICA CREDENCIAIS CORRETAS
    apply_oci_environment(env)

    print(f"🔐 Ambiente OCI ativo: {env}")
    print(f"🔑 Key usada: {PRIVATE_KEY_PATH}")
    print(f"👤 USER_OCID: {USER_OCID}")
    print(f"🔐 FINGERPRINT: {FINGERPRINT}")

    # 🔥 3) VALIDA QUE AS CREDENCIAIS FORAM DEFINIDAS
    if not USER_OCID or not FINGERPRINT:
        print(f"❌ Erro: USER_OCID ou FINGERPRINT não definidos após aplicar ambiente {env}")
        return None

    # 🔥 4) VERIFICA SE O ARQUIVO DE CHAVE EXISTE
    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"❌ Erro: Arquivo de chave não encontrado em '{PRIVATE_KEY_PATH}'")
        return None

    # 🔥 5) AGORA SIM pode chamar Identity API
    try:
        private_key = load_private_key()
    except Exception as e:
        print(f"❌ Erro ao carregar chave privada: {e}")
        return None

    host = f"identity.{REGION}.oraclecloud.com"
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    request_target = (
        f"/20160918/compartments?"
        f"compartmentId={TENANCY_OCID}&compartmentIdInSubtree=true&name={quote(name)}"
    )

    signing_string = f"(request-target): get {request_target}\ndate: {now}\nhost: {host}"
    try:
        signature = sign_request(private_key, signing_string)
    except Exception as e:
        print(f"❌ Erro ao assinar requisição: {e}")
        return None

    key_id = f"{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}"
    headers = {
        "Date": now,
        "Host": host,
        "Authorization": (
            f'Signature version="1",'
            f'keyId="{key_id}",'
            f'algorithm="rsa-sha256",'
            f'headers="(request-target) date host",'
            f'signature="{signature}"'
        )
    }

    url = f"https://{host}{request_target}"
    print(f"🌐 Resolvendo compartment - URL: {url}")
    print(f"📋 Compartment name: {name}")

    resp = requests.get(url, headers=headers)
    if not resp.ok:
        print(f"❌ Erro ao buscar compartment '{name}': {resp.status_code} {resp.text}")
        print(f"🔍 Debug - keyId usado: {key_id}")
        print(f"🔍 Debug - request_target: {request_target}")
        return None

    payload = resp.json()

    if isinstance(payload, list):
        compartments = payload
    else:
        compartments = payload.get("data", [])

    if not compartments:
        print(f"⚠️ Compartment '{name}' não encontrado na tenancy.")
        return None

    ocid = compartments[0]["id"]
    print(f"📁 Compartment '{name}' -> {ocid}")
    return ocid


# ====== BUCKETS ======

def create_bucket(bucket_name: str, compartment: str):
    """
    Cria bucket no compartment especificado.
    'compartment' pode ser OCID (ocid1.compartment...) ou nome (ex: cp-infra-ddw3-dev).
    Retorna dict: {"ok": True, "compartment_id": "<ocid>"} ou {"ok": False, "error": "..."}
    """
    namespace = get_namespace()
    if not namespace:
        return {"ok": False, "error": "namespace not found"}

    # resolve compartment se for nome
    if not _is_ocid_compartment(compartment):
        resolved = resolve_compartment_ocid(compartment)
        if not resolved:
            return {"ok": False, "error": f"Compartment '{compartment}' não encontrado"}
        compartment_ocid = resolved
    else:
        compartment_ocid = compartment

    # prepare payload
    payload = {
        "name": bucket_name,
        "compartmentId": compartment_ocid,
        "publicAccessType": "NoPublicAccess",
        "storageTier": "Standard",
        "versioning": "Disabled",
        "objectEventsEnabled": False
    }

    json_compact = json.dumps(payload, separators=(',', ':'))
    body_bytes = json_compact.encode("utf-8")
    content_length = len(body_bytes)

    # sign
    private_key = load_private_key()
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(body_bytes)
    content_sha256 = base64.b64encode(hasher.finalize()).decode()

    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/"
    signing_string = (
        f"(request-target): post {request_target}\n"
        f"date: {now}\n"
        f"host: {HOST}\n"
        f"content-type: application/json\n"
        f"content-length: {content_length}\n"
        f"x-content-sha256: {content_sha256}"
    )
    signature = sign_request(private_key, signing_string)

    headers = {
        "Date": now,
        "Host": HOST,
        "Content-Type": "application/json",
        "Content-Length": str(content_length),
        "x-content-sha256": content_sha256,
        "Authorization": (
            f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
            f'algorithm="rsa-sha256",headers="(request-target) date host content-type content-length x-content-sha256",'
            f'signature="{signature}"'
        ),
    }

    url = f"https://{HOST}{request_target}"
    print(f"🌐 Criando bucket - URL: {url}")
    print(f"📦 Bucket: {bucket_name}, Compartment OCID: {compartment_ocid}")

    try:
        resp = requests.post(url, headers=headers, data=body_bytes)
    except requests.exceptions.RequestException as e:
        print("❌ Erro HTTP ao criar bucket:", e)
        return {"ok": False, "error": str(e)}

    if resp.status_code in (200, 201):
        print(f"✅ Bucket '{bucket_name}' criado com sucesso em {compartment_ocid}.")
        return {"ok": True, "compartment_id": compartment_ocid}
    else:
        print(f"❌ Erro ao criar bucket ({resp.status_code})")
        print(resp.text)
        return {"ok": False, "status_code": resp.status_code, "error": resp.text}


def list_buckets(compartment: Optional[str] = None):
    """
    Lista buckets dentro de 'compartment' (OCID or name). Se None usa COMPARTMENT_OCID (env) ou tenancy root fallback.
    Retorna lista de buckets (ou []).
    """
    namespace = get_namespace()
    if not namespace:
        return []

    # resolve target compartment OCID
    target = compartment
    if target:
        if not _is_ocid_compartment(target):
            resolved = resolve_compartment_ocid(target)
            if not resolved:
                print(f"⚠️ Não encontrei compartment '{target}' para listar buckets.")
                return []
            target = resolved
    else:
        # usar COMPARTMENT_OCID se definido, senão TENANCY_OCID (pode não listar tudo)
        target = COMPARTMENT_OCID or TENANCY_OCID

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/?compartmentId={target}"
    signing_string = f"(request-target): get {request_target}\ndate: {now}\nhost: {HOST}"
    signature = sign_request(private_key, signing_string)

    headers = {
        "Date": now,
        "Host": HOST,
        "Authorization": (
            f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
            f'algorithm="rsa-sha256",headers="(request-target) date host",signature="{signature}"'
        )
    }

    url = f"https://{HOST}{request_target}"
    print(f"🌐 Listando buckets - URL: {url}")
    print(f"📁 Compartment OCID: {target}")

    try:
        resp = requests.get(url, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro HTTP ao listar buckets: {e}")
        return []

    if not resp.ok:
        print(f"❌ Erro ao listar buckets: {resp.status_code} {resp.text}")
        return []

    try:
        buckets = resp.json()
    except Exception as e:
        print("❌ Erro ao decodificar JSON da listagem de buckets:", e)
        return []

    # buckets é uma lista; mantenha compatibilidade
    if not buckets:
        print("📭 Nenhum bucket encontrado.")
        return []

    for b in buckets:
        name = b.get("name", "<sem-nome>")
        created = b.get("timeCreated", "-")
        print(f"📦 {name}  (Created: {created})")

    return buckets

# ====== OBJETOS ======
def upload_file(bucket_name, file_path, object_name=None):
    if not os.path.isfile(file_path):
        print(f"❌ Arquivo não encontrado: {file_path}")
        return

    if object_name is None:
        object_name = os.path.basename(file_path)

    print(f"⬆️  Enviando '{file_path}' para o bucket '{bucket_name}' como '{object_name}'...")

    namespace = get_namespace()
    if not namespace:
        print("❌ Namespace não encontrado.")
        return

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/{bucket_name}/o/{quote(object_name)}"

    # Detectar o tipo MIME do arquivo
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = "application/octet-stream"

    with open(file_path, "rb") as f:
        file_data = f.read()

    content_length = len(file_data)
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(file_data)
    content_sha256 = base64.b64encode(hasher.finalize()).decode()

    signing_string = (
        f"(request-target): put {request_target}\n"
        f"date: {now}\n"
        f"host: {HOST}\n"
        f"content-type: {content_type}\n"
        f"content-length: {content_length}\n"
        f"x-content-sha256: {content_sha256}"
    )

    signature = sign_request(private_key, signing_string)
    authorization = (
        f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
        f'algorithm="rsa-sha256",headers="(request-target) date host content-type content-length x-content-sha256",'
        f'signature="{signature}"'
    )

    headers = {
        "Date": now,
        "Host": HOST,
        "Content-Type": content_type,
        "Content-Length": str(content_length),
        "x-content-sha256": content_sha256,
        "Authorization": authorization
    }

    url = f"https://{HOST}{request_target}"

    try:
        response = requests.put(url, headers=headers, data=file_data)
        if response.status_code in [200, 201]:
            print("✅ Upload concluído com sucesso.")
            return True
        else:
            print(f"❌ Erro no upload (HTTP {response.status_code})")
            print(response.text)
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Falha ao fazer upload: {e}")
        return False

def list_objects(bucket_name):
    print(f"📂 Listando objetos do bucket '{bucket_name}'...")

    namespace = get_namespace()
    if not namespace:
        print("❌ Namespace não encontrado.")
        return []

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/{bucket_name}/o"
    signing_string = f"(request-target): get {request_target}\ndate: {now}\nhost: {HOST}"
    signature = sign_request(private_key, signing_string)

    headers = {
        "Date": now,
        "Host": HOST,
        "Authorization": (
            f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
            f'algorithm="rsa-sha256",headers="(request-target) date host",signature="{signature}"'
        ),
    }

    url = f"https://{HOST}{request_target}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        objects = response.json().get("objects", [])
        if not objects:
            print("📭 Nenhum objeto encontrado.")
        else:
            for obj in objects:
                name = obj.get("name")
                size = obj.get("size")
                created = obj.get("timeCreated")
                print(f"📄 {name} ({size} bytes) - criado em {created}")
        return objects
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao listar objetos: {e}")
        return []

def delete_object(bucket_name, object_name):
    print(f"🗑️  Deletando objeto '{object_name}' do bucket '{bucket_name}'...")

    namespace = get_namespace()
    if not namespace:
        print("❌ Namespace não encontrado.")
        return False

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/{bucket_name}/o/{quote(object_name)}"
    signing_string = f"(request-target): delete {request_target}\ndate: {now}\nhost: {HOST}"
    signature = sign_request(private_key, signing_string)

    authorization = (
        f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
        f'algorithm="rsa-sha256",headers="(request-target) date host",signature="{signature}"'
    )

    headers = {
        "Date": now,
        "Host": HOST,
        "Authorization": authorization
    }

    url = f"https://{HOST}{request_target}"

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code in [200, 204]:
            print(f"✅ Objeto '{object_name}' deletado com sucesso.")
            return True
        else:
            print(f"❌ Erro ao deletar objeto (HTTP {response.status_code})")
            print(response.text)
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição: {e}")
        return False

def delete_bucket(bucket_name):
    print(f"🗑️  Deletando bucket '{bucket_name}'...")

    namespace = get_namespace()
    if not namespace:
        print("❌ Namespace não encontrado.")
        return False

    private_key = load_private_key()
    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_target = f"/n/{namespace}/b/{bucket_name}"
    signing_string = f"(request-target): delete {request_target}\ndate: {now}\nhost: {HOST}"
    signature = sign_request(private_key, signing_string)

    authorization = (
        f'Signature version="1",keyId="{TENANCY_OCID}/{USER_OCID}/{FINGERPRINT}",'
        f'algorithm="rsa-sha256",headers="(request-target) date host",signature="{signature}"'
    )

    headers = {
        "Date": now,
        "Host": HOST,
        "Authorization": authorization
    }

    url = f"https://{HOST}{request_target}"

    try:
        response = requests.delete(url, headers=headers)
        if response.status_code in [200, 204]:
            print(f"✅ Bucket '{bucket_name}' deletado com sucesso.")
            return True
        elif response.status_code == 409:
            print("❌ Erro: Bucket não está vazio.")
            return False
        else:
            print(f"❌ Erro ao deletar bucket (HTTP {response.status_code})")
            print(response.text)
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de requisição: {e}")
        return False
