"""Agnes API 客户端核心模块。

职责单一：封装密钥读取、配置加载、HTTP 请求（含重试）。
不承担任何业务逻辑（剧本、分镜等），业务由上层脚本负责。

安全：密钥仅从环境变量 AGNES_API_KEY 读取，绝不写入文件或日志。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

CONFIG_PATH = Path(__file__).resolve().parent / "agnes_config.yaml"


@dataclass
class AgnesConfig:
    """Agnes API 配置。"""

    base_url: str
    text_model: str
    image_model: str
    video_model: str
    site: str

    @classmethod
    def load(cls, config_path: Path = CONFIG_PATH) -> "AgnesConfig":
        """从 YAML 配置加载。无需 PyYAML —— 使用极简解析，避免额外依赖。"""
        raw = _parse_simple_yaml(config_path)
        site = raw.get("site", "cn")
        sites = raw.get("sites", {})
        base_url = sites.get(site, {}).get("base_url", "https://api.agnes-ai.cn/v1")
        models = raw.get("models", {})
        return cls(
            base_url=base_url.rstrip("/"),
            text_model=models.get("text", "agnes-3.0-flash"),
            image_model=models.get("image", "agnes-image-2.5-flash"),
            video_model=models.get("video", "agnes-video-2.5-flash"),
            site=site,
        )


def _parse_simple_yaml(path: Path) -> dict[str, Any]:
    """极简 YAML 解析：仅支持两层嵌套 + 标量值。

    避免引入 PyYAML 依赖。若配置超出该复杂度需换用正式解析器。
    """
    result: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    indent_stack: list[tuple[int, dict[str, Any]]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].rstrip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        if ":" not in stripped:
            continue
        key, _, value = stripped.strip().partition(":")
        key, value = key.strip(), value.strip()

        if not value:  # 嵌套节点
            node: dict[str, Any] = {}
            if indent == 0:
                result[key] = node
            else:
                target = indent_stack[-1][1] if indent_stack else result
                target[key] = node
            indent_stack.append((indent, node))
        else:
            target = indent_stack[-1][1] if indent_stack and indent > indent_stack[-1][0] else result
            target[key] = _coerce(value)
    return result


def _coerce(value: str) -> Any:
    """标量类型转换。"""
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value.strip('"').strip("'")


# ---------------------------------------------------------------------------
# 密钥
# ---------------------------------------------------------------------------

class MissingAPIKeyError(RuntimeError):
    """未找到 AGNES_API_KEY。"""


ENV_PATH = Path(__file__).resolve().parent / ".env"


def _read_dotenv(path: Path) -> str | None:
    """从 .env 文件读取 AGNES_API_KEY（简易解析，不引入第三方库）。"""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("AGNES_API_KEY=") and not line.startswith("#"):
            value = line.split("=", 1)[1].strip().strip('"').strip("'")
            return value or None
    return None


def get_api_key() -> str:
    """读取密钥，优先级：系统环境变量 > scripts/.env 文件。

    找不到时抛出明确异常。绝不打印密钥内容。
    """
    # 1) 系统环境变量（优先级最高）
    key = os.environ.get("AGNES_API_KEY", "").strip()
    if key and key != "YOUR_API_KEY_HERE":
        return key

    # 2) 项目内 .env 文件（已在 .gitignore 中排除）
    key = _read_dotenv(ENV_PATH)
    if key and key != "YOUR_API_KEY_HERE":
        return key

    raise MissingAPIKeyError(
        "未检测到 AGNES_API_KEY。请选一种方式配置：\n"
        "  方式1（推荐）：cmd 中执行 setx AGNES_API_KEY \"你的密钥\"，然后重启 WorkBuddy\n"
        "  方式2：编辑 scripts/.env 文件，填入 AGNES_API_KEY=你的密钥\n"
    )


def key_source() -> str:
    """返回密钥来源描述，用于自检报告（不泄露内容）。"""
    env_key = os.environ.get("AGNES_API_KEY", "").strip()
    if env_key and env_key != "YOUR_API_KEY_HERE":
        return "系统环境变量"
    dotenv_key = _read_dotenv(ENV_PATH)
    if dotenv_key and dotenv_key != "YOUR_API_KEY_HERE":
        return "scripts/.env 文件"
    return "未配置"


def has_api_key() -> bool:
    """检测密钥是否就绪（不抛异常）。"""
    try:
        get_api_key()
        return True
    except MissingAPIKeyError:
        return False


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

class AgnesAPIError(RuntimeError):
    """Agnes API 返回错误。"""


def request_json(
    config: AgnesConfig,
    method: str,
    endpoint: str,
    payload: dict[str, Any] | None = None,
    timeout: int = 120,
    max_retries: int = 3,
) -> dict[str, Any]:
    """发送 JSON 请求并返回解析结果。

    endpoint 形如 "/chat/completions"，会自动拼接 base_url。
    对 5xx 与网络错误做指数退避重试；4xx 直接抛出（不重试）。
    """
    url = f"{config.base_url}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            if 400 <= e.code < 500:
                # 客户端错误不重试
                raise AgnesAPIError(f"HTTP {e.code} @ {endpoint}: {detail}") from e
            last_error = AgnesAPIError(f"HTTP {e.code} @ {endpoint}: {detail}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_error = e

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # 指数退避 2s, 4s

    raise AgnesAPIError(f"请求失败（已重试 {max_retries} 次）: {last_error}")


def download_file(url: str, dest: Path, timeout: int = 300) -> Path:
    """下载 URL 到本地文件。用于保存生成的图片/视频。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())
    return dest
