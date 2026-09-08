"""
Configuração central da aplicação.

Decisão de arquitetura: TODA configuração sensível vem de variáveis de
ambiente (nunca hardcoded). Em produção, essas variáveis são injetadas
pelo Secrets Manager (Vault/KMS) no processo de deploy, não versionadas
no repositório. O .env.example mostra apenas quais chaves existem.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Banco de dados
    database_url: str = "sqlite:///./dev.db"

    # JWT
    jwt_secret_key: str = "CHANGE_ME_IN_PRODUCTION_VIA_SECRETS_MANAGER"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15  # curta duração de propósito
    refresh_token_expire_minutes: int = 60 * 24 * 7

    # Rate limiting (submissões de flag)
    flag_submission_max_attempts_per_minute: int = 5

    # Lab isolation defaults
    lab_default_ttl_minutes: int = 60
    lab_cpu_limit: str = "1.0"          # 1 vCPU
    lab_memory_limit: str = "512m"      # 512 MB
    lab_pids_limit: int = 100           # anti fork-bomb
    lab_disk_limit_mb: int = 512

    # Range provider: "docker" (MVP/dev local) ou "kubernetes" (Fase 4+).
    # Decisão: a escolha do provider é 100% configuração, nunca código
    # espalhado com if/else — quem consome (lab_sessions router) só
    # conhece a interface comum (provision/destroy), nunca o backend
    # concreto. Isso permite trocar de Docker Compose local para um
    # cluster Kubernetes em produção sem tocar em app/routers/.
    range_provider: str = "docker"
    k8s_runtime_class: str = "gvisor"       # runtime hardened (gVisor/Kata)
    k8s_namespace_prefix: str = "vantage-lab-"
    k8s_platform_namespace: str = "vantage-range-platform"

    # Worker de expiração automática
    expiration_worker_poll_seconds: int = 60

    # Ambiente
    environment: str = "development"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
