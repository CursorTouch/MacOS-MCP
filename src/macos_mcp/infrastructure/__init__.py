"""Infrastructure layer — cross-cutting concerns: auth, security, analytics, config, oauth."""

from macos_mcp.infrastructure.auth import AuthKeyMiddleware, OAuthOnlyMiddleware, is_loopback_host
from macos_mcp.infrastructure.security import (
    IPAllowlistMiddleware,
    parse_ip_allowlist,
    validate_url,
)
from macos_mcp.infrastructure.analytics import Analytics, PostHogAnalytics, with_analytics
from macos_mcp.infrastructure.config import (
    MacOSMCPConfig,
    ServerConfig,
    SecurityConfig,
    ToolsConfig,
    discover_config_path,
    load_config,
)
from macos_mcp.infrastructure.oauth import OAuthStore, build_oauth_routes, validate_oauth_token

__all__ = [
    "AuthKeyMiddleware",
    "OAuthOnlyMiddleware",
    "is_loopback_host",
    "IPAllowlistMiddleware",
    "parse_ip_allowlist",
    "validate_url",
    "Analytics",
    "PostHogAnalytics",
    "with_analytics",
    "MacOSMCPConfig",
    "ServerConfig",
    "SecurityConfig",
    "ToolsConfig",
    "discover_config_path",
    "load_config",
    "OAuthStore",
    "build_oauth_routes",
    "validate_oauth_token",
]
