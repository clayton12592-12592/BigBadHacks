"""Microsoft -> Xbox -> Minecraft login (device-code flow), stdlib only.

You sign in on Microsoft's own website with a short code; this script never
sees your password. It stores a refresh token in auth_cache.json so you only
have to do this once. KEEP THAT FILE PRIVATE - anyone with it can log in as you.

Uses the public client id of the official Minecraft Java launcher
(00000000402b5328). Two login endpoints are tried in order.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

LAUNCHER_ID = "00000000402b5328"
MS_V2 = "https://login.microsoftonline.com/consumers/oauth2/v2.0"
FLOWS = [
    {   # classic live.com device-code login
        "name": "live", "client_id": LAUNCHER_ID,
        "device": "https://login.live.com/oauth20_connect.srf",
        "token": "https://login.live.com/oauth20_token.srf",
        "scope": "service::user.auth.xboxlive.com::MBI_SSL",
        "extra": {"response_type": "device_code"},
        "rps": ["t=", "d="],
    },
    {   # newer Microsoft identity platform endpoint
        "name": "v2", "client_id": LAUNCHER_ID,
        "device": f"{MS_V2}/devicecode",
        "token": f"{MS_V2}/token",
        "scope": "XboxLive.signin offline_access",
        "extra": {},
        "rps": ["d=", "t="],
    },
]
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_cache.json")


def _request(url, data=None, js=None, headers=None):
    if js is not None:
        body, ctype = json.dumps(js).encode(), "application/json"
    elif data is not None:
        body, ctype = urllib.parse.urlencode(data).encode(), "application/x-www-form-urlencoded"
    else:
        body, ctype = None, None
    h = {"Accept": "application/json", **(headers or {})}
    if ctype:
        h["Content-Type"] = ctype
    req = urllib.request.Request(url, body, h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return {"_http_error": e.code, **json.loads(raw)}
        except Exception:
            return {"_http_error": e.code}
    return json.loads(raw) if raw else {}


def _device_login(flow):
    d = _request(flow["device"], data={"client_id": flow["client_id"],
                                       "scope": flow["scope"], **flow["extra"]})
    if "device_code" not in d:
        raise RuntimeError(f"[{flow['name']}] device-code request failed: {d}")
    print("\n" + "=" * 60)
    print(f" Open  {d['verification_uri']}  and enter the code:  {d['user_code']}")
    print("=" * 60 + "\n", flush=True)
    deadline = time.time() + int(d.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(int(d.get("interval", 5)))
        t = _request(flow["token"], data={
            "client_id": flow["client_id"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": d["device_code"],
        })
        if "access_token" in t:
            return t
        if t.get("error") not in ("authorization_pending", "slow_down"):
            raise RuntimeError(f"[{flow['name']}] Microsoft login failed: {t}")
    raise RuntimeError("Microsoft login timed out")


def _refresh(flow, refresh_token):
    t = _request(flow["token"], data={
        "client_id": flow["client_id"], "grant_type": "refresh_token",
        "refresh_token": refresh_token, "scope": flow["scope"],
    })
    return t if "access_token" in t else None


def _minecraft(flow, ms_token):
    xbl = {}
    for prefix in flow["rps"]:           # ticket format differs between endpoints
        xbl = _request("https://user.auth.xboxlive.com/user/authenticate", js={
            "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com",
                           "RpsTicket": prefix + ms_token},
            "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"})
        if "Token" in xbl:
            break
    if "Token" not in xbl:
        raise RuntimeError(f"Xbox Live login failed: {xbl}")
    xsts = _request("https://xsts.auth.xboxlive.com/xsts/authorize", js={
        "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl["Token"]]},
        "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"})
    if "Token" not in xsts:
        raise RuntimeError(f"XSTS failed (no Xbox profile / child account?): {xsts}")
    uhs = xsts["DisplayClaims"]["xui"][0]["uhs"]
    mc = _request("https://api.minecraftservices.com/authentication/login_with_xbox",
                  js={"identityToken": f"XBL3.0 x={uhs};{xsts['Token']}"})
    if "access_token" not in mc:
        raise RuntimeError(f"Minecraft login failed: {mc}")
    prof = _request("https://api.minecraftservices.com/minecraft/profile",
                    headers={"Authorization": "Bearer " + mc["access_token"]})
    if "id" not in prof:
        raise RuntimeError(f"No Minecraft Java profile on this account: {prof}")
    return {"access_token": mc["access_token"], "uuid": prof["id"], "name": prof["name"]}


def _save(flow, tokens):
    with open(CACHE, "w") as f:
        json.dump({"flow": flow["name"], "refresh_token": tokens.get("refresh_token", "")}, f)


def login():
    """Return {'access_token', 'uuid' (no dashes), 'name'}. Blocking."""
    # 1) silent login from the saved refresh token
    if os.path.exists(CACHE):
        try:
            saved = json.load(open(CACHE))
            flow = next(f for f in FLOWS if f["name"] == saved["flow"])
            tokens = _refresh(flow, saved["refresh_token"])
            if tokens:
                _save(flow, {"refresh_token": tokens.get("refresh_token", saved["refresh_token"])})
                return _minecraft(flow, tokens["access_token"])
        except Exception as e:
            print("Saved login didn't work, signing in again:", e)
    # 2) interactive device-code login, trying each endpoint in turn
    errors = []
    for flow in FLOWS:
        try:
            tokens = _device_login(flow)
        except RuntimeError as e:
            errors.append(str(e))
            continue
        _save(flow, tokens)
        return _minecraft(flow, tokens["access_token"])
    raise RuntimeError("All Microsoft login methods failed:\n  " + "\n  ".join(errors))


def server_hash(server_id, secret, public_key_der):
    """Minecraft's signed-hex SHA-1 used by the session server."""
    h = hashlib.sha1()
    h.update(server_id.encode("ascii"))
    h.update(secret)
    h.update(public_key_der)
    return format(int.from_bytes(h.digest(), "big", signed=True), "x")


def join_server(access_token, uuid, server_hash_hex):
    """Tell Mojang we're about to join a server (required by online-mode)."""
    r = _request("https://sessionserver.mojang.com/session/minecraft/join", js={
        "accessToken": access_token, "selectedProfile": uuid, "serverId": server_hash_hex})
    if r.get("_http_error"):
        raise RuntimeError(f"Mojang session server refused the join: {r}")
