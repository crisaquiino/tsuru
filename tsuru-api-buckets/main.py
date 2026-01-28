# main.py
import tempfile
import oci
import base64
from pathlib import Path
from typing import Optional
from fastapi import Request, FastAPI, UploadFile, Query, File, Form, Body, HTTPException, Header
from fastapi.responses import JSONResponse
from requests import request
import oci_client as oc
import re
from fastapi import Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Header, HTTPException, Depends
from typing import List, Dict, Any
from get_user_groups_and_roles import get_user_member_of, get_access_token
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response


FRONT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://ddw3-tsuru-front-s3.apps.tsuru.gcp.i.globo",
]


readme = Path(__file__).with_name("README.md").read_text(encoding="utf-8")
def sanitize_input(val):
    if val is None:
        return None
    if isinstance(val, str):
        v = val.strip()
        if not v:
            return None
        if v.lower() in ("null", "none", "undefined"):
            return None
        return v
    return val

# extrai token cp-... de uma label/group (retorna None se não achar)
_RE_CP_TOKEN = re.compile(r"(cp[-_][A-Za-z0-9\-_]+)", re.I)
def extract_child_from_group_label(label: str):
    if not label:
        return None
    m = _RE_CP_TOKEN.search(label)
    return m.group(1) if m else None

app = FastAPI(
    title="ddw3-tsuru-api-s3",
    version="1.0.0",
    description=readme,               
    docs_url="/",                 
    redoc_url="/redoc",               
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONT_ORIGINS,  # porta do Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/__routes")
def show_routes():
    return [{"path": r.path, "methods": list(r.methods)} for r in app.routes]
@app.options("/login")
def login_options():
    return Response(status_code=200)

@app.post("/login")
def login(payload: dict = Body(...)):
    """
    Endpoint simples de login por email (DEV).
    Recebe JSON: {"email":"usuario@dominio.com"}
    Retorna: {"access_token": "...", "token_type": "bearer"}
    """
    email = (payload or {}).get("email")
    if not email:
        raise HTTPException(status_code=422, detail="email required")

    # validação simples de formato (apenas básica)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="email inválido")

    # Token de desenvolvimento — substitua por JWT / OAuth2 em produção.
    token = f"dev-token-for-{email}"
    return {"access_token": token, "token_type": "bearer"}

def get_current_email_from_auth(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(401, "Authorization header required")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Invalid auth header")
    token = parts[1]
    if token.startswith("dev-token-for-"):
        return token[len("dev-token-for-"):]
    # TODO: decode JWT here in prod
    raise HTTPException(401, "Unsupported token")

@app.get("/user/groups")
def api_user_groups(current_email: str = Depends(get_current_email_from_auth),
                    token: str = Depends(get_access_token),):
    """
    Retorna a lista completa de 'memberOf' do usuário identificado por current_email.
    Resposta: {"email":"...","memberOf":[{"id":"...", "displayName":"...", "@odata.type":"..."} , ...]}
    """
    try:
        member_of = get_user_member_of(current_email, token)  # retorna lista já paginada
    except Exception as e:
        # log opcional
        print(f"[ERROR] get_user_member_of({current_email}): {e}")
        raise HTTPException(status_code=502, detail=f"Erro ao consultar Graph: {e}")

    # Filtrar/formatar a resposta para o front (evita expor chaves indesejadas)
    simplified = []
    for item in member_of:
        simplified.append({
            "id": item.get("id"),
            "displayName": item.get("displayName"),
            "odata_type": item.get("@odata.type")
        })

    return {"email": current_email, "memberOf": simplified}

@app.get("/")
def root():
    return {
        "name": "ddw3-tsuru-api-s3",
        "ok": True,
        "docs": "/docs",
        "health": "/health"
    }
# ---------- Health ----------
@app.get("/health")
def health():
    return {"ok": True}

# ---------- Namespace ----------
@app.get("/namespace")
def get_ns():
    ns = oc.get_namespace()
    if not ns:
        return JSONResponse({"error": "namespace not found"}, status_code=500)
    return {"namespace": ns}

# ---------- Buckets ----------

@app.post("/buckets")
async def api_create_bucket(
    request: Request,
    name: Optional[str] = Query(None, description="Nome do bucket (required)"),
    child: Optional[str] = Query(None, description="Child OCID ou nome (optional)"),
    group: Optional[str] = Query(None, description="Label de grupo (ex: OCI-Administrators-cp-... ) (optional)")
):
    print("DEBUG RAW QUERY:", request.url)
    # ler body/form também (prioridade query > form > json)
    try:
        form = await request.form()
    except Exception:
        form = None
    try:
        body_json = await request.json()
    except Exception:
        body_json = None

    bucket_name = name or (form.get("name") if form else None) or (body_json.get("name") if isinstance(body_json, dict) else None)
    child = child or (form.get("child") if form else None) or (body_json.get("child") if isinstance(body_json, dict) else None)
    group = group or (form.get("group") if form else None) or (body_json.get("group") if isinstance(body_json, dict) else None)

    bucket_name = sanitize_input(bucket_name)
    child = sanitize_input(child)
    group = sanitize_input(group)

    if not bucket_name:
        raise HTTPException(status_code=422, detail="Envie 'name' (nome do bucket) via query/form/json")

    # se o front enviou a label do grupo, extraímos o token cp-...
    if not child and group:
        child = extract_child_from_group_label(group)
        print(f"DEBUG: extracted child from group '{group}' -> {child}")

    if not child:
        raise HTTPException(status_code=422, detail="Envie 'child' (OCID or name) ou 'group' (label)")

    # se já for OCID, usamos direto; senão resolvemos para OCID via oci_client
    if child.startswith("ocid1.compartment"):
        child_ocid = child
    else:
        child_ocid = oc.resolve_compartment_ocid(child)
        if not child_ocid:
            raise HTTPException(status_code=404, detail=f"Compartment '{child}' não encontrado (resolve failed)")

    print(f"DEBUG: creating bucket '{bucket_name}' in compartment {child_ocid}")

    result = oc.create_bucket(bucket_name, child_ocid)
    if not result.get("ok"):
        # repassa erro da camada oc com status
        err = result.get("error") or result
        status_code = result.get("status_code", 400)
        raise HTTPException(status_code=status_code, detail=f"Erro criando bucket: {err}")

    return {
        "created": True,
        "bucket": bucket_name,
        "compartment_ocid": result.get("compartment_id") or child_ocid
    }

@app.get("/buckets")
def api_list_buckets(child: Optional[str] = Query(None, description="Child OCID ou nome (ex: cp-infra-ddw3-dev)"),
                     group: Optional[str] = Query(None, description="Label de grupo (opcional)")):
    # sanitize
    child = sanitize_input(child)
    group = sanitize_input(group)

    # se enviaram group, extrair token cp-...
    if not child and group:
        child = extract_child_from_group_label(group)
        print(f"DEBUG: extracted child from group '{group}' -> {child}")

    if not child:
        # se nenhum child, usa fallback do oc.list_buckets (COMPARTMENT_OCID ou TENANCY)
        buckets = oc.list_buckets(compartment=None)
        return {"buckets": buckets}

    # resolve ocid se necessário
    if child.startswith("ocid1.compartment"):
        child_ocid = child
    else:
        child_ocid = oc.resolve_compartment_ocid(child)
        if not child_ocid:
            return {"buckets": [], "warning": f"Compartment '{child}' não encontrado"}

    buckets = oc.list_buckets(compartment=child_ocid) or []
    return {"buckets": buckets}

@app.delete("/buckets/{bucket}")
def api_delete_bucket(bucket: str):
    ok = oc.delete_bucket(bucket)
    return {"deleted": bool(ok), "bucket": bucket}

# ---------- Objetos ----------
@app.get("/buckets/{bucket}/objects")
def api_list_objects(bucket: str):
    # Se seu oci_client.list_objects ainda só imprimir, caímos em [].
    objects = oc.list_objects(bucket)
    if objects is None:
        objects = []
    return {"bucket": bucket, "objects": objects}

@app.delete("/buckets/{bucket}/objects/{object_name:path}")
def api_delete_object(bucket: str, object_name: str):
    ok = oc.delete_object(bucket, object_name)
    return {"deleted": bool(ok), "bucket": bucket, "object": object_name}

@app.post("/buckets/{bucket}/upload")
async def api_upload(
    bucket: str,
    request: Request,
    # multipart "padrão"
    file: UploadFile = File(None),
    object_name_form: Optional[str] = Form(None),

    # alternativas
    object_name_q: Optional[str] = Query(None, alias="object_name"),
    x_object_name: Optional[str] = Header(None, convert_underscores=False, alias="X-Object-Name"),
    json_body: Optional[dict] = Body(None),
):
    """
    Aceita:
      1) multipart/form-data: file=<arquivo>, [object_name=<nome>]
      2) JSON: {"content_b64": "<base64>", "object_name": "<nome>"}
      3) Corpo binário: Body (binary) e object_name via query (?object_name=) ou header X-Object-Name
    """
    # Nome do objeto pode vir de vários lugares
    object_name = object_name_q or x_object_name or object_name_form

    # (1) multipart/form-data
    if file is None:
        # Se o campo tiver outro nome, pega o primeiro UploadFile do form
        try:
            form = await request.form()
            for k, v in form.items():
                if isinstance(v, UploadFile):
                    file = v
                    if not object_name:
                        object_name = form.get("object_name") or v.filename
                    break
        except Exception:
            pass

    if file is not None:
        data = await file.read()
        if not object_name:
            object_name = file.filename or "upload.bin"
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(data)
            tmp.flush()
            ok = oc.upload_file(bucket, tmp.name, object_name)
        return {"uploaded": bool(ok), "bucket": bucket, "object": object_name}

    # (2) JSON com base64
    if json_body:
        b64 = json_body.get("content_b64")
        if b64:
            try:
                data = base64.b64decode(b64, validate=True)
            except Exception:
                raise HTTPException(status_code=422, detail="content_b64 inválido (base64 esperado)")
            if not object_name:
                object_name = json_body.get("object_name")
            if not object_name:
                raise HTTPException(status_code=422, detail="Defina 'object_name' no JSON ou via ?object_name=/X-Object-Name")
            with tempfile.NamedTemporaryFile(delete=True) as tmp:
                tmp.write(data)
                tmp.flush()
                ok = oc.upload_file(bucket, tmp.name, object_name)
            return {"uploaded": bool(ok), "bucket": bucket, "object": object_name}

    # (3) Corpo binário bruto
    raw = await request.body()
    if raw:
        if not object_name:
            raise HTTPException(status_code=422, detail="Envie 'object_name' via query (?object_name=) ou header X-Object-Name")
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            tmp.write(raw)
            tmp.flush()
            ok = oc.upload_file(bucket, tmp.name, object_name)
        return {"uploaded": bool(ok), "bucket": bucket, "object": object_name}

    raise HTTPException(
        status_code=422,
        detail="Envie o arquivo como form-data (file), JSON (content_b64 + object_name) ou corpo binário (+ object_name por query/header)."
    )

