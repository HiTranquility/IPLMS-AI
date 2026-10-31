"""Luật đầu vào cho connection model LLM (IPLMS ADR-0061 §6–§7, chống SSRF).

Thuần, không gọi mạng: phân giải DNS và mở socket nằm ở
`app/infra/llm/connection_probe.py`, nó gọi `check_resolved_addresses` với IP
thật đã phân giải trước khi kết nối, nên tên miền trỏ về IP cấm vẫn bị chặn.
"""
from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network
from urllib.parse import urlsplit

PROVIDERS = ("ollama", "local", "openai")
# Tên biến secret được phép (Q-B đã chốt): tiền tố riêng hoặc nằm trong allowlist cấu hình.
SECRET_PREFIX = "AI_LLM_KEY_"
_SECRET_NAME = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_NAME = re.compile(r"^[\w .()-]{2,80}$")

# Luôn chặn, kể cả host có trong allowlist: metadata cloud và dải link-local.
_METADATA = frozenset({
    ip_address("169.254.169.254"),  # AWS / GCP / Azure / OpenStack
    ip_address("fd00:ec2::254"),    # AWS IPv6
    ip_address("100.100.100.200"),  # Alibaba Cloud
})
_ALWAYS_BLOCKED_NETS = (ip_network("169.254.0.0/16"), ip_network("fe80::/10"))


class BlockedEndpoint(ValueError):
    """Endpoint bị chặn bởi allowlist hoặc dải IP cấm."""


def _split_list(raw: str) -> frozenset[str]:
    return frozenset(item.strip().lower() for item in (raw or "").split(",") if item.strip())


def allowed_hosts(raw: str) -> frozenset[str]:
    return _split_list(raw)


def normalize_base_url(raw: str, hosts: frozenset[str]) -> str:
    """Trả base URL đã chuẩn hoá; host ngoài allowlist hoặc IP cấm thì ném `BlockedEndpoint`."""
    url = (raw or "").strip()
    if len(url) > 500:
        raise ValueError("Endpoint dài quá 500 ký tự.")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("Endpoint phải là URL http(s) có host.")
    if parts.username or parts.password:
        # Thông tin đăng nhập trong URL sẽ bị lưu và hiện ra; key phải nằm ở env.
        raise ValueError("Endpoint không được chứa user/password.")
    if parts.query or parts.fragment:
        raise ValueError("Endpoint không được có query hoặc fragment.")
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("Cổng của endpoint không hợp lệ.") from exc
    host = parts.hostname.lower()
    if host not in hosts:
        raise BlockedEndpoint(f"Host '{host}' chưa có trong allowlist AI_CONSOLE_MODEL_CONNECTION_HOSTS.")
    try:
        literal = ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        check_resolved_addresses([literal])
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    return f"{parts.scheme}://{netloc}{parts.path.rstrip('/')}"


def check_resolved_addresses(addresses) -> None:
    """Chặn khi BẤT KỲ địa chỉ nào rơi vào metadata/link-local/không định tuyến được."""
    if not addresses:
        raise BlockedEndpoint("Không phân giải được host.")
    for raw in addresses:
        address = raw if isinstance(raw, (IPv4Address, IPv6Address)) else ip_address(raw)
        mapped = getattr(address, "ipv4_mapped", None)
        if mapped is not None:
            address = mapped
        if (
            address in _METADATA
            or any(address in net for net in _ALWAYS_BLOCKED_NETS)
            or address.is_unspecified
            or address.is_multicast
            # Python xếp `::1` vào is_reserved (::/8); loopback thì cho qua như IPv4.
            or (address.is_reserved and not address.is_loopback)
        ):
            raise BlockedEndpoint(f"Địa chỉ {address} bị chặn (metadata/link-local).")


def clean_secret_env_name(raw: str, provider: str, extra_allowed: str) -> str:
    name = (raw or "").strip()
    if not name:
        if provider == "openai":
            raise ValueError("Connection OpenAI cần tên biến env chứa key.")
        return ""
    if not _SECRET_NAME.match(name):
        raise ValueError("Tên biến secret: chữ IN HOA, số, gạch dưới, tối đa 64 ký tự.")
    if not name.startswith(SECRET_PREFIX) and name.lower() not in _split_list(extra_allowed):
        raise ValueError(
            f"Tên biến secret phải bắt đầu bằng {SECRET_PREFIX} hoặc nằm trong "
            "AI_CONSOLE_MODEL_SECRET_NAMES."
        )
    return name


def clean_connection(raw: dict, hosts: frozenset[str], extra_secret_names: str) -> dict:
    name = " ".join(str(raw.get("name") or "").split())
    if not _NAME.match(name):
        raise ValueError("Tên connection cần 2–80 ký tự (chữ, số, khoảng trắng, . ( ) -).")
    provider = str(raw.get("provider") or "")
    if provider not in PROVIDERS:
        raise ValueError("Provider chỉ nhận ollama, local hoặc openai.")
    return {
        "name": name,
        "provider": provider,
        "base_url": normalize_base_url(str(raw.get("base_url") or ""), hosts),
        "secret_env_name": clean_secret_env_name(
            str(raw.get("secret_env_name") or ""), provider, extra_secret_names,
        ),
    }
