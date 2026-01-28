# app_logger.py
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Diretório de logs
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def log_action(action: str, user: str, details: Optional[dict] = None):
    """
    Registra uma ação do usuário em um arquivo de log.
    
    Args:
        action: Tipo de ação (ex: "login", "create_bucket", "delete_bucket")
        user: Email do usuário que realizou a ação
        details: Dicionário com informações adicionais (ex: nome do bucket, compartment, etc.)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "action": action,
        "user": user,
        "details": details or {}
    }
    
    # Nome do arquivo de log baseado na data (um arquivo por dia)
    log_filename = f"app_{datetime.now().strftime('%Y-%m-%d')}.log"
    log_path = LOGS_DIR / log_filename
    
    # Escreve o log em formato JSON (uma linha por entrada)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # Se houver erro ao escrever o log, imprime mas não quebra a aplicação
        print(f"⚠️ Erro ao escrever log: {e}")


def log_login(user: str):
    """Registra um login de usuário."""
    log_action("login", user, {"event": "user_login"})


def log_create_bucket(user: str, bucket_name: str, compartment_ocid: Optional[str] = None):
    """Registra a criação de um bucket."""
    log_action("create_bucket", user, {
        "bucket_name": bucket_name,
        "compartment_ocid": compartment_ocid
    })


def log_delete_bucket(user: str, bucket_name: str):
    """Registra a deleção de um bucket."""
    log_action("delete_bucket", user, {
        "bucket_name": bucket_name
    })
