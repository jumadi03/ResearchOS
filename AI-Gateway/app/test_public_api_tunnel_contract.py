from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = (ROOT / "deploy" / "compose.yaml").read_text(encoding="utf-8")
STACK_ENV_EXAMPLE = (ROOT / "deploy" / "stack.env.example").read_text(
    encoding="utf-8"
)


def test_api_remains_loopback_bound_while_tunnel_is_profile_gated() -> None:
    assert 'ports: ["127.0.0.1:8080:8000"]' in COMPOSE
    assert 'profiles: ["public-api"]' in COMPOSE
    assert "cloudflare/cloudflared:2026.7.2" in COMPOSE
    assert "TUNNEL_TOKEN: ${CLOUDFLARED_TUNNEL_TOKEN:-}" in COMPOSE


def test_tunnel_waits_for_api_health_and_token_is_never_committed() -> None:
    assert "api: {condition: service_healthy}" in COMPOSE
    assert "CLOUDFLARED_TUNNEL_TOKEN=" in STACK_ENV_EXAMPLE
    assert "CLOUDFLARED_TUNNEL_TOKEN=\n" in STACK_ENV_EXAMPLE
