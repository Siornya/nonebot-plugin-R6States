"""
对 R6Data API 的封装，从上游 npm 包 `r6-data.js` 移植。

用法:
    from .r6data import R6Client

    r6 = R6Client(api_key="YOUR_KEY")
    info = await r6.players.get_profile("PlayerName", "uplay")
    ops  = await r6.game.get_operators(side="attacker")
    await r6.aclose()
"""

from __future__ import annotations
from typing import Any, Optional, Mapping
import httpx

#: 本移植对标的 r6-data.js 版本
BASED_ON_VERSION = "3.3.0"

#: API 地址
BASE_URL = "https://public-api.arenyze.com/r6/api"

#: v7 对应 Y11S2 起的 Ranked 3.0
VALID_RANK_VERSIONS = ("v1", "v2", "v3", "v4", "v5", "v6", "v7")

VALID_OPERATOR_MODES = (
    "all", "ranked", "standard", "unranked", "quick-match", "casual",
    "dual-front", "siege-cup",
)

VALID_FULL_STATS_MODES = ("ranked", "standard", "casual", "all")

# 平台类型供调用方参考；V2 平台族在 profile / leaderboard 中校验。
PLATFORM_TYPES = ("uplay", "psn", "xbl")
PLATFORM_FAMILIES = ("pc", "psn", "xbl")

__all__ = [
    "R6Client",
    "Players",
    "Game",
    "R6APIError",
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


# ──────────────────────────────────────────────────────────────────────────
# 资源:Players
# ──────────────────────────────────────────────────────────────────────────

class Players:
    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def get_profile(self, name_on_platform: str, platform_type: str,
                          platform_families: Optional[str] = None) -> Any:
        """V2 完整档案：account、stats、banned、seasons、history 和 meta。

        platform_families 可选 pc/psn/xbl，省略时由服务端推断。
        可选数据缺失时由 meta.partial / meta.errors 描述，原样返回。
        """
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        if platform_families and platform_families not in PLATFORM_FAMILIES:
            raise ValueError(
                "Invalid platform_families. Must be one of: " + ", ".join(PLATFORM_FAMILIES))
        return await self._client._get("/v2/profile", {
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
            "platform_families": platform_families,
        })

    async def get_operator_stats(self, name_on_platform: str, platform_type: str,
                                 season_year: Optional[str] = None,
                                 modes: Optional[str] = None) -> Any:
        """V2 干员战绩，支持 VALID_OPERATOR_MODES 中的模式。"""
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        if modes and modes not in VALID_OPERATOR_MODES:
            raise ValueError("Invalid modes. Must be one of: " + ", ".join(VALID_OPERATOR_MODES))
        params = {
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
            "modes": modes,
        }
        if season_year:
            params["seasonYear"] = season_year
        return await self._client._get("/v2/operators", params)

    async def get_leaderboard(self, *, page: Optional[int] = None,
                              platform: Optional[str] = None) -> Any:
        """V2 排行榜：页码 1～50，平台 pc/psn/xbl。"""
        if page is not None and (type(page) is not int or not 1 <= page <= 50):
            raise ValueError("Invalid page. Must be an integer between 1 and 50")
        if platform and platform not in PLATFORM_FAMILIES:
            raise ValueError("Invalid platform. Must be one of: " + ", ".join(PLATFORM_FAMILIES))
        return await self._client._get("/v2/leaderboard", {"page": page, "platform": platform})

    async def get_full_stats(self, name_on_platform: str, platform_type: str,
                             season_year: Optional[str] = None,
                             modes: Optional[str] = None) -> Any:
        """文档中的 V2 完整快照，返回原始 player / filters / fullStats 响应。

        fullStats 包含 operators、platform_families_full_profiles、data
        和 totalsHoursPlayed。上游 JS SDK 尚未封装此接口。
        modes: ranked|standard|casual|all；season_year: 赛季代码或 all。
        """
        if not name_on_platform or not platform_type:
            raise ValueError("Missing required parameters: name_on_platform, platform_type")
        if platform_type not in PLATFORM_TYPES:
            raise ValueError("Invalid platform_type. Must be one of: " + ", ".join(PLATFORM_TYPES))
        if modes and modes not in VALID_FULL_STATS_MODES:
            raise ValueError("Invalid modes. Must be one of: " + ", ".join(VALID_FULL_STATS_MODES))
        params = {
            "nameOnPlatform": name_on_platform,
            "platformType": platform_type,
        }
        if season_year:
            params["seasonYear"] = season_year
        if modes:
            params["modes"] = modes
        return await self._client._get("/v2/fullstats", params)


# ──────────────────────────────────────────────────────────────────────────
# 资源:Game(静态数据)
# ──────────────────────────────────────────────────────────────────────────

class Game:
    def __init__(self, client: "R6Client") -> None:
        self._client = client

    async def get_game_stats(self) -> Any:
        return await self._client._get("/v2/gamestats", {})

    async def get_twitch_stats(self) -> Any:
        return await self._client._get("/v2/twitchstats", {})

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
            data = await r6.players.get_profile("Name", "uplay", "pc")
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
