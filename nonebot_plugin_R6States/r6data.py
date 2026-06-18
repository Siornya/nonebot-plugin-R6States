"""
对 https://api.r6data.com/api 的封装，从官方 npm 包 `r6-data.js` 移植修改而来。

用法:
    from .r6data import R6Client

    r6 = R6Client(api_key="YOUR_KEY")
    info = await r6.players.get_account_info("PlayerName", "uplay")
    ops  = await r6.game.get_operators(side="attacker")
    await r6.aclose()
"""

from __future__ import annotations
from typing import Any, Optional, Sequence, Mapping
import httpx

#: 本移植对标的 r6-data.js 版本。启动时与 npm 最新版比对。
BASED_ON_VERSION = "3.1.7"

#: 上游历史上换过一次域名 (r6data.eu -> r6data.com)。如再变,改这里。
BASE_URL = "https://api.r6data.com/api"

#: getRanks 接受的 version 取值;新赛季可能新增 v7...
VALID_RANK_VERSIONS = ("v1", "v2", "v3", "v4", "v5", "v6")

#: getPlayerStats / 对比时 board_id 的合法取值
VALID_BOARD_IDS = ("casual", "event", "warmup", "standard", "ranked")

# 平台 / 平台族(供调用方参考,运行时不强校验)
PLATFORM_TYPES = ("uplay", "psn", "xbl")
PLATFORM_FAMILIES = ("pc", "console")

__all__ = [
    "R6Client",
    "Players",
    "Game",
    "R6APIError",
    "check_latest_version",
    "BASED_ON_VERSION",
    "BASE_URL",
]


# ──────────────────────────────────────────────────────────────────────────
# 错误类型
# ──────────────────────────────────────────────────────────────────────────

class R6APIError(Exception):
    """非 2xx 响应抛出。``status`` / ``data`` 携带服务端返回内容。"""

    def __init__(self, message: str, *, status: Optional[int] = None,
                 data: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.data = data


def _clean_params(params: Mapping[str, Any]) -> dict[str, str]:
    """丢弃 None/空串,其余转字符串 —— 对应原库 buildUrlAndParams。"""
    out: dict[str, str] = {}
    for key, value in params.items():
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = str(value)
    return out


def _validate_board_id(board_id: Optional[str]) -> None:
    if board_id and board_id not in VALID_BOARD_IDS:
        raise ValueError(
            "Invalid board_id. Must be one of: " + ", ".join(VALID_BOARD_IDS)
        )


def _filter_board_profiles(data: Any, board_id: Optional[str]) -> None:
    """原库 filterBoardProfiles:就地把每个 profile 的 board_ids_full_profiles
    过滤成只剩指定 board_id。"""
    if not board_id or not isinstance(data, dict):
        return
    profiles = data.get("platform_families_full_profiles")
    if not isinstance(profiles, list):
        return
    for profile in profiles:
        boards = profile.get("board_ids_full_profiles")
        if isinstance(boards, list):
            profile["board_ids_full_profiles"] = [
                b for b in boards if b.get("board_id") == board_id
            ]


# ──────────────────────────────────────────────────────────────────────────
# 资源:Players
# ──────────────────────────────────────────────────────────────────────────

class Players:
    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def get_account_info(self, name_on_platform: str,
                               platform_type: str) -> Any:
        """玩家账号信息 (type=accountInfo)。"""
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        return await self._client._get("/stats", {
            "type": "accountInfo",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        })

    async def get_is_banned(self, name_on_platform: str,
                            platform_type: str) -> Any:
        """封禁状态 (type=isBanned)。"""
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        return await self._client._get("/stats", {
            "type": "isBanned",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        })

    async def get_player_stats(self, name_on_platform: str, platform_type: str,
                               platform_families: str,
                               board_id: Optional[str] = None) -> Any:
        """玩家战绩 (type=stats)。给了 board_id 会就地过滤结果。"""
        if not name_on_platform or not platform_type or not platform_families:
            raise ValueError(
                "Missing required parameters: name_on_platform, platform_type, platform_families")
        _validate_board_id(board_id)
        params = {
            "type": "stats",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
            "platform_families": platform_families,
        }
        if board_id:
            params["board_id"] = board_id
        data = await self._client._get("/stats", params)
        _filter_board_profiles(data, board_id)
        return data

    async def get_player_comparisons(
        self,
        players: Sequence[Mapping[str, str]],
        platform_families: str,
        board_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """对比多名玩家。每个 player 形如
        {"nameOnPlatform": ..., "platformType": ...}。逐个查询并汇总,
        单个失败不影响其余(对应原库行为)。"""
        if not players or len(players) < 2:
            raise ValueError("At least 2 players are required for comparison")
        if not platform_families:
            raise ValueError("Missing required parameter: platform_families")
        for i, p in enumerate(players):
            if not p.get("nameOnPlatform") or not p.get("platformType"):
                raise ValueError(
                    f"Player {i + 1} is missing required fields: nameOnPlatform, platformType")
        _validate_board_id(board_id)

        comparisons: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for player in players:
            params = {
                "type": "stats",
                "nameOnPlatform": player["nameOnPlatform"],
                "platformType": player["platformType"],
                "platform_families": platform_families,
            }
            if board_id:
                params["board_id"] = board_id
            try:
                data = await self._client._get("/stats", params)
                _filter_board_profiles(data, board_id)
                profiles = (data or {}).get("platform_families_full_profiles") or []
                if profiles:
                    comparisons.append({"player": player, "stats": data, "success": True})
                else:
                    comparisons.append({"player": player, "stats": None,
                                        "success": False, "error": "No stats found for player"})
            except Exception as exc:  # noqa: BLE001 - 单玩家失败需被收集而非中断
                errors.append({"player": player, "error": str(exc)})
                comparisons.append({"player": player, "stats": None,
                                    "success": False, "error": str(exc)})

        result: dict[str, Any] = {"comparisons": comparisons}
        if errors:
            result["errors"] = errors
        return result

    async def get_operator_stats(self, name_on_platform: str, platform_type: str,
                                 season_year: Optional[str] = None,
                                 modes: Optional[str] = None) -> Any:
        """干员维度战绩 (type=operatorStats)。modes: ranked|casual|unranked。"""
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        params = {
            "type": "operatorStats",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
            "modes": modes,
        }
        if season_year:
            params["seasonYear"] = season_year
        return await self._client._get("/stats", params)

    async def get_full_stats(self, name_on_platform: str, platform_type: str,
                             season_year: Optional[str] = None,
                             modes: Optional[str] = None) -> Any:
        """完整快照 (type=fullStats)。单请求合并三套数据：

        - ``operators``：等同 operatorStats
        - ``platform_families_full_profiles``：各 board(ranked/casual/...)完整档案
        - ``data``：tracker 风格的 metadata/segments/platformInfo(等级、段位段等)

        modes: ranked|casual|unranked|quick-match|standard|all（默认 all）。
        season_year: 如 "Y10S4" 或 "all"（默认 all，不按赛季过滤）。
        """
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        params = {
            "type": "fullStats",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        }
        if season_year:
            params["seasonYear"] = season_year
        if modes:
            params["modes"] = modes
        return await self._client._get("/stats", params)

    async def get_seasonal_stats(self, name_on_platform: str,
                                 platform_type: str) -> Any:
        """当前赛季战绩 (type=seasonalStats)。"""
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        return await self._client._get("/stats", {
            "type": "seasonalStats",
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        })


# ──────────────────────────────────────────────────────────────────────────
# 资源:Game(静态数据)
# ──────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def get_game_stats(self) -> Any:
        return await self._client._get("/stats", {"type": "gameStats"})

    async def get_maps(self, *, name: Optional[str] = None,
                       location: Optional[str] = None,
                       release_date: Optional[str] = None,
                       playlists: Optional[str] = None,
                       map_reworked: Optional[bool] = None) -> Any:
        return await self._client._get("/maps", {
            "name": name, "location": location, "releaseDate": release_date,
            "playlists": playlists, "mapReworked": map_reworked,
        })

    async def get_operators(self, *, name: Optional[str] = None,
                            safename: Optional[str] = None,
                            realname: Optional[str] = None,
                            birthplace: Optional[str] = None,
                            age: Optional[int] = None,
                            date_of_birth: Optional[str] = None,
                            season_introduced: Optional[str] = None,
                            health: Optional[int] = None,
                            speed: Optional[int] = None,
                            unit: Optional[str] = None,
                            country_code: Optional[str] = None,
                            roles: Optional[str] = None,
                            side: Optional[str] = None) -> Any:
        return await self._client._get("/operators", {
            "name": name, "safename": safename, "realname": realname,
            "birthplace": birthplace, "age": age, "date_of_birth": date_of_birth,
            "season_introduced": season_introduced, "health": health,
            "speed": speed, "unit": unit, "country_code": country_code,
            "roles": roles, "side": side,
        })

    async def get_ranks(self, *, name: Optional[str] = None,
                        min_mmr: Optional[int] = None,
                        max_mmr: Optional[int] = None,
                        version: Optional[str] = None) -> Any:
        if version and version not in VALID_RANK_VERSIONS:
            raise ValueError(
                "Version not valid. Choose between " + ", ".join(VALID_RANK_VERSIONS) + ".")
        return await self._client._get("/ranks", {
            "name": name, "min_mmr": min_mmr, "max_mmr": max_mmr, "version": version,
        })

    async def get_seasons(self, *, name: Optional[str] = None,
                          map: Optional[str] = None,
                          operators: Optional[str] = None,
                          weapons: Optional[str] = None,
                          description: Optional[str] = None,
                          code: Optional[str] = None,
                          start_date: Optional[str] = None) -> Any:
        return await self._client._get("/seasons", {
            "name": name, "map": map, "operators": operators, "weapons": weapons,
            "description": description, "code": code, "startDate": start_date,
        })

    async def get_weapons(self, *, name: Optional[str] = None) -> Any:
        return await self._client._get("/weapons", {"name": name})

    async def get_charms(self, *, name: Optional[str] = None,
                         collection: Optional[str] = None,
                         rarity: Optional[str] = None,
                         availability: Optional[str] = None,
                         bundle: Optional[str] = None,
                         season: Optional[str] = None) -> Any:
        return await self._client._get("/charms", {
            "name": name, "collection": collection, "rarity": rarity,
            "availability": availability, "bundle": bundle, "season": season,
        })

    async def get_universal_skins(self, *, name: Optional[str] = None) -> Any:
        return await self._client._get("/universalSkins", {"name": name})

    async def get_attachment(self, *, name: Optional[str] = None,
                             style: Optional[str] = None,
                             rarity: Optional[str] = None,
                             availability: Optional[str] = None,
                             bundle: Optional[str] = None,
                             season: Optional[str] = None) -> Any:
        return await self._client._get("/attachment", {
            "name": name, "style": style, "rarity": rarity,
            "availability": availability, "bundle": bundle, "season": season,
        })

    async def get_search_all(self, query: str) -> Any:
        if not query or not isinstance(query, str):
            raise ValueError("Search query is required and must be a string")
        return await self._client._get("/searchAll", {"q": query})

    async def get_service_status(self) -> Any:
        return await self._client._get("/serviceStatus", {})


# ──────────────────────────────────────────────────────────────────────────
# 主客户端
# ──────────────────────────────────────────────────────────────────────────

class R6Client:
    """
    用法::

        r6 = R6Client(api_key="...")
        try:
            data = await r6.players.get_player_stats("Name", "uplay", "pc")
        finally:
            await r6.aclose()

    也可作为异步上下文管理器::

        async with R6Client(api_key="...") as r6:
            ...
    """

    def __init__(self, api_key: str, *, base_url: str = BASE_URL,
                 timeout: float = 15.0,
                 client: Optional[httpx.AsyncClient] = None) -> None:
        if not api_key:
            raise ValueError("Missing required config parameter: api_key")
        self.api_key = api_key
        self._base_url = base_url.rstrip("/")
        # 允许外部注入共享的 AsyncClient(例如复用 NoneBot 的);否则自建。
        self._http = client or httpx.AsyncClient(timeout=timeout)
        self._owns_http = client is None

        self.players = Players(self)
        self.game = Game(self)

    async def __aenter__(self) -> "R6Client":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """关闭内部创建的 httpx client(注入的不会被关闭)。"""
        if self._owns_http:
            await self._http.aclose()

    async def _get(self, path: str, params: Mapping[str, Any]) -> Any:
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": f"r6data.py (port of r6-data.js@{BASED_ON_VERSION})",
            "api-key": self.api_key,
        }
        resp = await self._http.get(url, params=_clean_params(params), headers=headers)
        return self._handle(resp)

    @staticmethod
    def _handle(resp: httpx.Response) -> Any:
        text = resp.text
        data: Any = None
        if text:
            try:
                data = resp.json()
            except ValueError:
                data = text
        if resp.is_success:
            return data
        if resp.status_code == 401:
            raise R6APIError("Authentication error", status=401, data=data)
        raise R6APIError(
            f"Request failed with status code {resp.status_code}",
            status=resp.status_code, data=data,
        )


# ──────────────────────────────────────────────────────────────────────────
# 启动时版本检查
# ──────────────────────────────────────────────────────────────────────────

_NPM_LATEST_URL = "https://registry.npmjs.org/r6-data.js/latest"


def _parse_semver(v: str) -> tuple[int, ...]:
    core = v.split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for piece in core.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


async def check_latest_version(*, timeout: float = 5.0) -> Optional[str]:
    """查 npm registry 上 r6-data.js 的最新版本号。

    成功返回版本字符串(如 "3.1.8");网络/解析失败返回 None(只告警、
    绝不阻塞启动)。比对建议::

        latest = await check_latest_version()
        if latest and _parse_semver(latest) > _parse_semver(BASED_ON_VERSION):
            logger.warning(...)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            resp = await c.get(_NPM_LATEST_URL,
                               headers={"Accept": "application/json"})
        if resp.is_success:
            version = resp.json().get("version")
            return version if isinstance(version, str) else None
    except Exception:  # noqa: BLE001 - 检查失败不应影响主流程
        return None
    return None


def is_outdated(latest: Optional[str]) -> bool:
    """latest 比 BASED_ON_VERSION 新则 True;latest 为 None 时 False。"""
    if not latest:
        return False
    return _parse_semver(latest) > _parse_semver(BASED_ON_VERSION)
