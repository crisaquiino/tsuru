import os
import sys
import msal
import requests
import oci_client
#import oci_manager
#import main
#from azure_graph import get_user_member_of

# Configurações do aplicativo (App Registration)
TENANT_ID = os.getenv("AZURE_TENANT_ID", "a7cdc447-3b29-4b41-b73e-8a2cb54b06c6")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "d94b1b1e-844a-4668-8909-1b8c5a500edc")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "mbZ8Q~-MuDkEm5ovzveDJtOqMU1NkGV6ixsbKc0f")

# Endpoint do Microsoft Graph
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def get_access_token():
    """Obtém um token de acesso usando client credentials (MSAL)."""
    app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
    )

    result = app.acquire_token_silent(SCOPE, account=None)

    if not result:
        result = app.acquire_token_for_client(scopes=SCOPE)

    if "access_token" not in result:
        raise Exception(f"Erro ao obter token: {result}")

    return result["access_token"]


def call_graph(endpoint, token, params=None):
    """Faz chamada ao Microsoft Graph e retorna o JSON."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = GRAPH_BASE_URL + endpoint
    response = requests.get(url, headers=headers, params=params)

    if not response.ok:
        raise Exception(f"Erro na chamada ao Graph {url}: {response.status_code} - {response.text}")

    return response.json()


def get_user_member_of(user_id, token):
    """
    Retorna tudo que o usuário é membro (grupos, roles, etc.)
    /users/{id}/memberOf
    """
    endpoint = f"/users/{user_id}/memberOf"
    results = []
    params = {"$select": "id,displayName"}
    data = call_graph(endpoint, token, params=params)
    results.extend(data.get("value", []))

    # Paginação (caso haja mais páginas)
    while "@odata.nextLink" in data:
        next_url = data["@odata.nextLink"]
        response = requests.get(
            next_url,
            headers={"Authorization": f"Bearer {token}"}
        )
        if not response.ok:
            raise Exception(f"Erro na paginação: {response.status_code} - {response.text}")
        data = response.json()
        results.extend(data.get("value", []))

    return results


def split_groups_and_roles(member_of_list):
    """Separa em grupos e roles com base no @odata.type."""
    groups = []
    roles = []

    for item in member_of_list:
        odata_type = item.get("@odata.type", "")
        # Grupos
        if "group" in odata_type.lower():
            groups.append(item)
        # Directory roles
        elif "directoryRole" in odata_type or "directoryrole" in odata_type.lower():
            roles.append(item)

    return groups, roles

def fetch_member_of(user_id: str):
    token = get_access_token()
    member_of = get_user_member_of(user_id, token)
    groups, roles = split_groups_and_roles(member_of)

    result = []

    # Grupos
    for g in groups:
        result.append({
            "id": g.get("id"),
            "displayName": g.get("displayName"),
            "odata_type": "group",
        })

    # Roles
    for r in roles:
        result.append({
            "id": r.get("id"),
            "displayName": r.get("displayName"),
            "odata_type": "role",
        })

    return result

def main():    
    if len(sys.argv) < 2:
        print("Uso: python get_user_groups_and_roles.py <USER_ID_OR_UPN>")
        sys.exit(1)

    user_id = sys.argv[1]

    print(f"Buscando grupos e perfis do usuário: {user_id}")
    token = get_access_token()

    member_of = get_user_member_of(user_id, token)
    groups, roles = split_groups_and_roles(member_of)

    print("\n=== GRUPOS DO USUÁRIO ===")
    if not groups:
        print("Nenhum grupo encontrado.")
    else:
        for g in groups:
            print(f"- {g.get('displayName')} ({g.get('id')})")

    print("\n=== ROLES / PERFIS (Directory Roles) DO USUÁRIO ===")
    if not roles:
        print("Nenhum role encontrado.")
    else:
        for r in roles:
            print(f"- {r.get('displayName')} ({r.get('id')})")


if __name__ == "__main__":
    main()
