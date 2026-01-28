# OCI Bucket Manager (Python CLI)

Este projeto é uma interface de linha de comando (CLI) para gerenciar buckets e objetos no Oracle Cloud (OCI) Object Storage usando requisições assinadas manualmente com chave privada.

## 🔧 Pré-requisitos

- Python 3.10+
- Pipenv ou virtualenv (recomendado)
- Chave privada `.pem` válida cadastrada no console da OCI
- Dependências instaladas:

```bash
pip install -r requirements.txt

# ddw3-tsuru-api-s3 — Guia de uso via linha de comando

Este documento descreve como interagir com a API `ddw3-tsuru-api-s3` exposta no Tsuru para gerenciar **buckets** e **objetos** no **OCI Object Storage** usando `curl` pela linha de comando.

> **Base URL da API**  
> `https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo`  
> Como seu ambiente exige certificado corporativo, nos exemplos abaixo usamos `-k` para ignorar a verificação TLS (não recomendado em produção).

---

 📋 Endpoints disponíveis

| Método | Rota                                                       | Descrição                                        |
|--------|------------------------------------------------------------|--------------------------------------------------|
| GET    | `/health`                                                  | Checa se a API está rodando                      |
| GET    | `/namespace`                                               | Obtém o namespace do OCI                         |
| GET    | `/buckets`                                                 | Lista todos os buckets                           |
| POST   | `/buckets`                                                 | Cria um bucket                                   |
| DELETE | `/buckets/{bucket}`                                        | Deleta um bucket vazio                           |
| GET    | `/buckets/{bucket}/objects`                                | Lista objetos de um bucket                       |
| POST   | `/buckets/{bucket}/upload`                                 | Faz upload de arquivo                            |
| DELETE | `/buckets/{bucket}/objects/{object_name}`                  | Deleta um objeto                                 |

---

 🩺 Teste de saúde da API

```bash
curl -kS https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/health | jq .

📜 Listar NameSpace
curl -kS https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/namespace

Criar bucket 📦
curl -kS -X POST "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets" \
  -H "Content-Type: application/json" \
  -d '{"name":"meu-bucket"}' | jq .

📂 Listar buckets
curl -kS "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets" | jq .

⬆️ Upload de arquivo para um bucket
#Teste usando meu repo local#
curl -kS -X POST "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets/meu-bucket/upload" \
  -F "file=@/home/cris/tsuru/ddw3-tsuru-api-s3/testeupload.txt" \
  -F "object_name=testeupload.txt" | jq .

📜 Listar objetos de um bucket
curl -kS "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets/meu-bucket/objects" | jq .

🗑️ Deletar um objeto
curl -kS -X DELETE "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets/meu-bucket/objects/testeupload.txt" | jq .

❌ Deletar um bucket
curl -kS -X DELETE "https://ddw3-tsuru-api-s3.apps.tsuru.gcp.i.globo/buckets/meu-bucket" | jq .
