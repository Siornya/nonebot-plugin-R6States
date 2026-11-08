"""HTTP contract tests, loading the client without starting NoneBot."""
import asyncio
import importlib.util
from pathlib import Path

import httpx

spec = importlib.util.spec_from_file_location(
    "r6data", Path(__file__).parents[1] / "nonebot_plugin_R6States/r6data.py")
r6data = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r6data)


def test_routes_and_upload(tmp_path):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"quota": {"remaining": 2}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            client = r6data.R6Client("test-key", client=http,
                                     base_url="https://stats.test/api/", site_base_url="https://site.test/api/")
            await client.players.get_full_stats("Player", "uplay", season_year="Y11S3", modes="ranked")
            replay = tmp_path / "round.REC"
            replay.write_bytes(b"round-data")
            await client.match_replay.upload_replays([replay, {"name": "second.rec", "data": b"second"}])
            await client.aclose()
            assert not http.is_closed

    asyncio.run(run())
    assert str(requests[0].url).startswith("https://stats.test/api/v2/fullstats?")
    assert requests[0].url.params["seasonYear"] == "Y11S3"
    upload = requests[1]
    assert upload.method == "POST"
    assert str(upload.url) == "https://site.test/api/replays/api/upload"
    assert upload.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert upload.content.count(b'name="replayFiles"') == 2
    assert b"round-data" in upload.content
    assert all(r.headers["api-key"] == "test-key" for r in requests)
