"""认证辅助：处理小米云端登录的二次验证"""

import json
import sys
from pathlib import Path

from src.config import get_settings, save_credentials
from src.micloud import MiCloud, VerificationRequired

SESSION_FILE = Path(__file__).parent.parent / ".mi_session"
TOKEN_FILE = Path(__file__).parent.parent / ".mi_token"


def initiate_login(username: str | None = None, password: str | None = None, country: str = "cn") -> dict:
    if username and password:
        save_credentials(username, password, country)

    s = get_settings()
    if not s.mi_username or not s.mi_password:
        return {"status": "missing_credentials", "message": "请提供小米账号和密码"}

    cloud = MiCloud(username=s.mi_username, password=s.mi_password, server=s.mi_cloud_country)

    try:
        cloud.login()
        _save_token(cloud)
        return {"status": "ok", "message": "登录成功，无需验证"}
    except VerificationRequired as e:
        session_data = {
            "auth_state": cloud._auth_state,
            "device_id": cloud.device_id,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f)
        return {"status": "verification_required", "message": str(e)}


def submit_verification(code: str) -> dict:
    if not SESSION_FILE.exists():
        return {"status": "error", "message": "请先调用 xiaomi_setup 发起登录"}

    with open(SESSION_FILE) as f:
        session_data = json.load(f)

    s = get_settings()
    cloud = MiCloud(username=s.mi_username, password=s.mi_password, server=s.mi_cloud_country)
    cloud._auth_state = session_data["auth_state"]
    cloud.device_id = session_data["device_id"]

    try:
        cloud.submit_verification(code)
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}

    _save_token(cloud)
    SESSION_FILE.unlink(missing_ok=True)

    devices = cloud.get_devices()
    device_summary = [
        {"name": d.get("name", "?"), "model": d.get("model", "?"), "online": d.get("isOnline", False)}
        for d in devices
    ]
    return {"status": "ok", "message": f"验证成功，共找到 {len(devices)} 个设备", "devices": device_summary}


def get_auth_status() -> dict:
    has_token = TOKEN_FILE.exists()
    s = get_settings()
    has_creds = bool(s.mi_username and s.mi_password)
    pending_verify = SESSION_FILE.exists()

    if has_token:
        return {"status": "authenticated", "message": "已认证，可正常使用"}
    if pending_verify:
        return {"status": "pending_verification", "message": "等待验证码，请调用 xiaomi_verify 提交验证码"}
    if has_creds:
        return {"status": "not_authenticated", "message": "已有账号信息，请调用 xiaomi_setup 发起登录"}
    return {"status": "not_configured", "message": "未配置账号，请调用 xiaomi_setup 提供小米账号和密码"}


def _save_token(cloud: MiCloud):
    token_data = {
        "cookies": cloud.cookies,
        "ssecurity": cloud.ssecurity.hex(),
        "server": cloud.server,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def load_cloud_from_token() -> MiCloud | None:
    if not TOKEN_FILE.exists():
        return None
    try:
        with open(TOKEN_FILE) as f:
            token_data = json.load(f)
        s = get_settings()
        cloud = MiCloud(username=s.mi_username, password=s.mi_password, server=s.mi_cloud_country)
        cloud.cookies = token_data["cookies"]
        cloud.ssecurity = bytes.fromhex(token_data["ssecurity"])
        cloud._logged_in = True
        return cloud
    except Exception:
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        if len(sys.argv) < 3:
            print("用法: uv run python -m src.auth_helper verify <验证码>")
            sys.exit(1)
        result = submit_verification(sys.argv[2])
        print(result["message"])
    else:
        result = initiate_login()
        print(result["message"])
