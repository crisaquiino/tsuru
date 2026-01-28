import argparse
from oci_client import (
    get_namespace,
    create_bucket,
    list_buckets,
    upload_file,
    list_objects,
    delete_object,
    delete_bucket
)

def main():
    parser = argparse.ArgumentParser(
        description="Gerenciador de buckets no Oracle Cloud (OCI Object Storage)",
        epilog="Exemplo: python oci_manager.py create meu-bucket"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Comando: list
    subparsers.add_parser("list_bucket", help="Listar todos os buckets")

    # Comando: create <bucket_name>
    create_parser = subparsers.add_parser("create", help="Criar um novo bucket")
    create_parser.add_argument("bucket_name", help="Nome do bucket a ser criado")

    # Comando: upload <bucket_name> <file_path> [object_name]
    upload_parser = subparsers.add_parser("upload", help="Fazer upload de arquivo para um bucket")
    upload_parser.add_argument("bucket_name")
    upload_parser.add_argument("file_path")
    upload_parser.add_argument("object_name", nargs="?")

    # Comando: list-objects <bucket_name>
    list_objects_parser = subparsers.add_parser("list-objects", help="Listar objetos de um bucket")
    list_objects_parser.add_argument("bucket_name")

    # Comando: delete-object <bucket_name> <object_name>
    delete_object_parser = subparsers.add_parser("delete-object", help="Deletar objeto de um bucket")
    delete_object_parser.add_argument("bucket_name")
    delete_object_parser.add_argument("object_name")

    # Comando: delete-bucket <bucket_name>
    delete_bucket_parser = subparsers.add_parser("delete-bucket", help="Deletar bucket (precisa estar vazio)")
    delete_bucket_parser.add_argument("bucket_name")

    args = parser.parse_args()

    # Sempre tenta obter o namespace antes de executar o comando
    namespace = get_namespace()
    if not namespace:
        print("❌ Namespace inválido. Abortando.")
        exit(1)

    # Aqui você conecta o comando ao código (temporariamente só imprime)
    match args.command:
        case "list_bucket":
            list_buckets()

        case "create":
            create_bucket(args.bucket_name)

        case "upload":
            upload_file(args.bucket_name, args.file_path, args.object_name)

        case "list-objects":
            list_objects(args.bucket_name)

        case "delete-object":
            delete_object(args.bucket_name, args.object_name)

        case "delete-bucket":
            delete_bucket(args.bucket_name)

        case _:
            print("❌ Comando não reconhecido.")


if __name__ == "__main__":
    main()