# Cloud poster for the meme page @sove7gn.clips. Runs inside a Composio COMPOSIO_REMOTE_WORKBENCH cell:
#   import requests; exec(requests.get("https://raw.githubusercontent.com/Sove7gn/sove7gn-clips-feed/main/post_next.py", timeout=30).text)
# (set DRY = True before the exec to test without posting).
#
# Stateless by design — Composio's sandbox storage is wiped between sessions, so nothing is stored there:
#   * queue + videos live in the GitHub repo Sove7gn/sove7gn-clips-feed (queue.json, reels/*.mp4)
#   * "already posted?" is decided from the meme page's own recent captions on Instagram
# Safety: posts ONLY via Composio account "instagram_hunger-vinous" and only if its IG id is the meme page
# 29285260837733822. The MAIN @sove7gn page is also connected (and is the default) — never post there.
import json, time, datetime, requests

RAW = "https://raw.githubusercontent.com/Sove7gn/sove7gn-clips-feed/main"
ACC = "instagram_hunger-vinous"
MEME_PAGE_ID = "29285260837733822"
MIN_GAP_MIN = 45


def _hook(caption):
    return (caption or "").split("\n")[0].strip().lower()


def _public_url(data, name):
    """Direct public URL Instagram can fetch (no redirects): uguu.se, then tmpfiles.org."""
    for _ in range(2):
        try:
            r = requests.post("https://uguu.se/upload", files={"files[]": (name, data, "video/mp4")}, timeout=60)
            return r.json()["files"][0]["url"]
        except Exception:
            time.sleep(2)
    r = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": (name, data, "video/mp4")}, timeout=60)
    return r.json()["data"]["url"].replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/", 1)


def post_next(dry=False, force=False):
    info, e = run_composio_tool("INSTAGRAM_GET_USER_INFO", {"ig_user_id": "me", "fields": "id,username"}, account=ACC)
    if e:
        return {"status": "error", "error": f"user info failed: {e}"}
    d = info["data"]
    if d.get("id") != MEME_PAGE_ID or d.get("username") == "sove7gn":
        return {"status": "error", "error": f"ABORTED: connection is @{d.get('username')}, not the meme page"}
    r, e = run_composio_tool("INSTAGRAM_GET_IG_USER_MEDIA", {"ig_user_id": "me", "limit": 60,
                             "fields": "caption,timestamp"}, account=ACC)
    if e:
        return {"status": "error", "error": f"media list failed: {e}"}
    recent = r["data"].get("data", [])
    if recent and not force:
        last = datetime.datetime.strptime(recent[0]["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        mins = (datetime.datetime.now(datetime.timezone.utc) - last).total_seconds() / 60
        if mins < MIN_GAP_MIN:
            return {"status": "skip", "reason": f"last post {mins:.0f} min ago"}
    posted = {_hook(m.get("caption")) for m in recent}
    queue = requests.get(f"{RAW}/queue.json", params={"t": int(time.time())}, timeout=30).json()
    todo = [q for q in queue if _hook(q["caption"]) not in posted]
    if not todo:
        return {"status": "empty", "queue": len(queue)}
    item = todo[0]
    if dry:
        return {"status": "dry-run", "account": d.get("username"), "next": item["slug"], "left": len(todo)}
    video = requests.get(f"{RAW}/reels/{item['file']}", timeout=60)
    video.raise_for_status()
    url = _public_url(video.content, item["file"])
    c, e = run_composio_tool("INSTAGRAM_POST_IG_USER_MEDIA", {
        "ig_user_id": d["id"], "media_type": "REELS", "video_url": url, "caption": item["caption"],
        "share_to_feed": True, "user_tags": [{"username": "sove7gn"}]}, account=ACC)
    if e:
        return {"status": "error", "error": f"create failed: {e}"}
    p, e = run_composio_tool("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {
        "ig_user_id": d["id"], "creation_id": c["data"]["id"], "max_wait_seconds": 90}, account=ACC)
    if e:
        return {"status": "error", "error": f"publish failed: {e}", "creation_id": c["data"]["id"]}
    m, e = run_composio_tool("INSTAGRAM_GET_IG_MEDIA", {"ig_media_id": p["data"]["id"], "fields": "permalink"}, account=ACC)
    link = (m or {}).get("data", {}).get("permalink", f"media id {p['data']['id']}")
    return {"status": "posted", "slug": item["slug"], "permalink": link, "left": len(todo) - 1}


RESULT = post_next(dry=globals().get("DRY", False), force=globals().get("FORCE", False))
print("RESULT:", json.dumps(RESULT))
RESULT
