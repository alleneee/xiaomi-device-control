"""认证辅助脚本：处理小米云端登录的二次验证"""

import json
import sys
from pathlib import Path

from src.config import get_settings
from src.micloud import MiCloud, VerificationRequired

SESSION_FILE = Path(__file__).parent.parent / ".mi_session"
TOKEN_FILE = Path(__file__).parent.parent / ".mi_token"


def step1_login():
    """第一步：登录并触发验证码"""
    s = get_settings()
    cloud = MiCloud(username=s.mi_username, password=s.mi_password, server=s.mi_cloud_country)

    try:
        cloud.login()
        _save_token(cloud)
        print("直接登录成功，无需验证!")
        return True
    except VerificationRequired as e:
        session_data = {
            "auth_state": cloud._auth_state,
            "device_id": cloud.device_id,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f)
        print(f"{e}")
        print("验证码已发送，请运行: uv run python -m src.auth_helper verify <验证码>")
        return False


def step2_verify(code: str):
    """第二步：提交验证码"""
    if not SESSION_FILE.exists():
        print("错误: 请先运行登录步骤")
        return False

    with open(SESSION_FILE) as f:
        session_data = json.load(f)

    s = get_settings()
    cloud = MiCloud(username=s.mi_username, password=s.mi_password, server=s.mi_cloud_country)
    cloud._auth_state = session_data["auth_state"]
    cloud.device_id = session_data["device_id"]

    cloud.submit_verification(code)
    _save_token(cloud)
    SESSION_FILE.unlink(missing_ok=True)
    print("验证成功!")

    devices = cloud.get_devices()
    print(f"\n共找到 {len(devices)} 个设备:")
    for d in devices:
        name = d.get("name", "?")
        model = d.get("model", "?")
        did = d.get("did", "?")
        ip = d.get("localip", "")
        online = d.get("isOnline", False)
        print(f"  - {name} | model={model} | did={did} | ip={ip} | online={online}")
    return True


def _save_token(cloud: MiCloud):
    """保存登录凭证，避免重复验证"""
    token_data = {
        "cookies": cloud.cookies,
        "ssecurity": cloud.ssecurity.hex(),
        "server": cloud.server,
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def load_cloud_from_token() -> MiCloud | None:
    """从保存的 token 恢复 MiCloud 实例"""
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
        step2_verify(sys.argv[2])
    else:
        step1_login()
