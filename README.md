# Vantage Range — MVP (Fase 2)

Plataforma corporativa de treinamento em segurança ofensiva. Este é o
**MVP** aprovado na Fase 2 do roadmap: autenticação, RBAC, um laboratório
funcional (Web Fundamentals), flags/scoring e dashboard.

> Todo laboratório aqui é isolado, fictício e efêmero — ver
> `docs/` (documento de arquitetura da Fase 1) para o modelo completo de
> isolamento e o threat model.

## Estrutura

```
vantage-range/
├── core-api/                      # Backend FastAPI
├── vulnerable-lab-web-fundamentals/  # App vulnerável do Lab 01 (IDOR proposital)
├── web/                            # Frontend Next.js
├── lab-templates/                  # Definições declarativas de labs (YAML)
├── docker-compose.dev.yml
└── .env.example
```

## Rodando localmente

### 1. Core API

```bash
cd core-api
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Gera dev.db (SQLite) com dados de demonstração:
# admin@vantage-range.example.com / instructor@... / student@...
# senha para todos: ChangeMe123!  (TROQUE em qualquer ambiente real)
JWT_SECRET_KEY=troque-por-um-valor-aleatorio ./venv/bin/python -m app.seed

JWT_SECRET_KEY=troque-por-um-valor-aleatorio ./venv/bin/uvicorn app.main:app --reload
# API em http://localhost:8000 — docs automáticas em /docs
```

Rodar os testes:

```bash
cd core-api
JWT_SECRET_KEY=test-secret ./venv/bin/python -m pytest tests/ -v
```

### 2. App vulnerável do Lab 01 (opcional, para explorar manualmente)

```bash
cd vulnerable-lab-web-fundamentals
python3 -m venv venv
./venv/bin/pip install flask==3.0.3
./venv/bin/python app.py
# http://localhost:8080 — login: alice/alice123 ou bob/bob123
# Vulnerabilidade: /profile/<id> não checa autorização (IDOR) —
# tente /profile/42 depois de logar como alice.
```

Em produção, esta app roda **dentro** de um container provisionado pelo
Range Orchestrator (`core-api/app/orchestrator.py`), nunca exposta
diretamente — aqui está sendo rodada fora de container apenas para você
explorar a lógica da vulnerabilidade rapidamente.

### 3. Frontend

```bash
cd web
npm install
cp .env.local.example .env.local   # aponta para http://localhost:8000
npm run dev
# http://localhost:3000
```

### 4. Docker Compose (Postgres + Redis + Core API)

```bash
cp .env.example .env    # edite POSTGRES_PASSWORD e JWT_SECRET_KEY
docker compose -f docker-compose.dev.yml up --build
```

## O que este MVP cobre (Fase 2 → Fase 5)

- Autenticação JWT (registro/login), sempre como `student` por padrão.
- RBAC real: `student`, `instructor`, `team_manager`, `org_admin`,
  `super_admin` — `team_manager` só gerencia o próprio team, nunca a
  organização inteira (testado explicitamente).
- **MFA (TOTP)** de ponta a ponta: setup gera QR/secret, só habilita
  depois de confirmado com um código válido, login com MFA exige uma
  segunda chamada com o segundo fator, e o token intermediário
  (`mfa_pending`) nunca é aceito como token de acesso normal.
- **Organizations/Teams multi-tenant**: `super_admin` cria organizações,
  `org_admin`/`team_manager` cria e gerencia teams e membros dentro da
  própria organização.
- **Analytics agregada** (`GET /analytics/overview`, org_admin+):
  usuários ativos, taxa de conclusão, score médio, labs mais difíceis
  por taxa de solve.
- **Reports profissionais** (`POST /reports/generate`): compila as
  flags corretas do usuário em um relatório estruturado (Executive
  Summary, Scope, Findings com severidade, Conclusion) — é um snapshot
  imutável no momento da geração.
- Lab 01 — Web Fundamentals (IDOR), com definição declarativa validada
  contra allowlist de imagens e isolamento de rede obrigatório.
- Dois providers de provisionamento (`docker`/`kubernetes`) atrás da
  mesma interface, com hardening completo em ambos (ver Fase 4 abaixo).
- Worker de expiração automática de labs.
- Flags como hash SHA-256, scoring com XP/nível, rate limiting.
- Learning Paths, Courses, Quizzes, Achievements (`first_blood`,
  `path_finisher`).
- Audit log append-only.
- **67 testes automatizados** cobrindo todas as fases.
- Frontend completo: dashboard, labs, learning paths com quiz, reports,
  teams, e fluxo de login com MFA.

## O que NÃO foi implementado (limitação real, não escondida)

- **SSO (OIDC) real**: requer um Identity Provider externo de verdade
  (Keycloak, Auth0, Okta) — não é algo que faz sentido simular sem um
  IdP real para integrar. A arquitetura já prevê o encaixe (ver Fase 1,
  seção "Autenticação": OAuth2/OIDC), mas a integração fica como
  próximo passo de infraestrutura, não de código de aplicação.
- Session Gateway dedicado (proxy real de acesso ao lab via
  noVNC/terminal web) — hoje `access_url` na resposta de
  `/lab-sessions` é um placeholder.
- CTF com ranking/leaderboard dedicado.
- Observabilidade completa (Prometheus/Grafana/OpenTelemetry).

## Rodando o provider Kubernetes (Fase 4)

Isso requer um cluster real com gVisor instalado nos nós — não é
executável neste ambiente de desenvolvimento sandbox. Para aplicar os
manifests em um cluster de verdade:

```bash
kubectl apply -f infra/k8s/base/runtimeclass-gvisor.yaml
kubectl apply -f infra/k8s/base/namespace-and-rbac.yaml
kubectl apply -f infra/k8s/base/networkpolicy-platform.yaml
kubectl apply -f infra/k8s/base/deployment-core-api.yaml
kubectl apply -f infra/k8s/base/cronjob-lab-expiration.yaml
```

Substitua os placeholders do `Secret core-api-secrets` pelo mecanismo
real do seu pipeline (Vault, External Secrets Operator, etc.) — nunca
edite esse arquivo com valores reais.

## Segurança — pontos que merecem atenção antes de qualquer deploy real

1. **Troque `JWT_SECRET_KEY`** — o valor default em `app/config.py` é
   apenas um placeholder de desenvolvimento.
2. **Troque as senhas do seed** (`ChangeMe123!`) antes de expor a API
   além do seu ambiente local.
3. O Core API monta o socket Docker do host (`docker-compose.dev.yml`)
   — isso é aceitável **apenas em dev local**. Em produção, isso é
   substituído pela API do Kubernetes com uma ServiceAccount de
   permissão mínima (ver documento de arquitetura da Fase 1, seção 6).
4. O token JWT no frontend fica em `localStorage` no MVP — antes de
   produção real, avaliar migrar para cookie httpOnly + refresh token
   rotativo (nota já deixada em `web/lib/api.ts`).
