# API Promo Milhas

API que lê mensagens de um grupo do Telegram com sua conta pessoal (MTProto), extrai promoções de viagens em milhas e as disponibiliza via REST.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Leitura do Telegram | Telethon (MTProto — conta pessoal) |
| API REST | FastAPI |
| Banco de dados | SQLite |
| Deploy | Docker + Docker Compose |

---

## Deploy na VPS (recomendado)

### Pré-requisitos

- Docker e Docker Compose instalados na VPS
- Credenciais do Telegram: acesse [my.telegram.org/apps](https://my.telegram.org/apps) e crie um app

---

### Passo 1 — Gerar a session string (faça localmente, uma única vez)

A autenticação MTProto exige que você confirme sua identidade interativamente (número de telefone + código). Faça isso uma vez na sua máquina local:

```bash
# Clone o projeto e instale as dependências
pip install telethon python-dotenv

# Copie e preencha o .env com API_ID, API_HASH e TELEGRAM_GROUP
cp .env.example .env

# Execute o script de autenticação
python generate_session.py
```

O script vai pedir seu número de telefone e o código recebido no Telegram.
Ao final, imprime uma linha como:

```
TELEGRAM_SESSION_STRING=1BVtsOKABu...longa string...
```

Copie essa string — ela vai no `.env` da VPS.

---

### Passo 2 — Configurar o .env na VPS

```bash
cp .env.example .env
```

Preencha o arquivo `.env`:

```env
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_GROUP=@nomeDoGrupo          # ou ID numérico: -1001234567890
TELEGRAM_SESSION_STRING=1BVtsOKABu...  # gerado no Passo 1
```

---

### Passo 3 — Subir o container

```bash
docker compose up -d --build
```

A API fica disponível em `http://<ip-da-vps>:8000`.

Para ver os logs:

```bash
docker compose logs -f
```

---

### Atualizar a aplicação

```bash
git pull
docker compose up -d --build
```

---

## Desenvolvimento local (sem Docker)

```bash
pip install -r requirements.txt
cp .env.example .env
# Preencha o .env (sem TELEGRAM_SESSION_STRING, o Telethon autentica interativamente)
python run.py
```

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/promotions` | Lista promoções com filtros |
| GET | `/promotions/{id}` | Busca promoção por ID |
| POST | `/sync` | Sincroniza histórico manualmente |
| GET | `/stats` | Estatísticas (companhias, programas, destinos) |
| GET | `/health` | Health check |

### Filtros em `GET /promotions`

| Parâmetro | Tipo | Exemplo |
|-----------|------|---------|
| `destination` | string | `MIAMI` |
| `airline` | string | `Latam` |
| `program` | string | `Latam Pass` |
| `max_miles` | int | `50000` |
| `origin_code` | string | `NVT` |
| `limit` | int (1–500) | `50` |
| `offset` | int | `0` |

---

## Estrutura do projeto

```
API Promo/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── models.py            # Pydantic models
│   ├── parser.py            # Parser de mensagens do Telegram
│   ├── storage.py           # Camada SQLite
│   └── telegram_client.py   # Telethon client (suporta StringSession)
├── data/                    # Volume Docker — banco SQLite persiste aqui
├── generate_session.py      # Script de autenticação (rode uma vez)
├── run.py                   # Entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
