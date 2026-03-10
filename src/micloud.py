"""小米云端 API 客户端，基于 XiaomiGateway3 项目的认证实现"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import string
import time
from typing import Any

import httpx
from cryptography.hazmat.primitives import ciphers
from cryptography.hazmat.decrepit.ciphers import algorithms

SDK_VERSION = "4.2.29"
BASE_URLS = {
    "cn": "https://api.io.mi.com/app",
    "de": "https://de.api.io.mi.com/app",
    "i2": "https://i2.api.io.mi.com/app",
    "ru": "https://ru.api.io.mi.com/app",
    "sg": "https://sg.api.io.mi.com/app",
    "us": "https://us.api.io.mi.com/app",
}

FLAG_PHONE = 4
FLAG_EMAIL = 8


class VerificationRequired(Exception):
    """需要手机/邮箱验证码"""
    def __init__(self, masked_contact: str, flag: int, identity_session: str):
        self.masked_contact = masked_contact
        self.flag = flag
        self.identity_session = identity_session
        contact_type = "手机" if flag == FLAG_PHONE else "邮箱"
        super().__init__(f"需要{contact_type}验证，验证码已发送到 {masked_contact}")


class MiCloud:
    def __init__(self, username: str, password: str, server: str = "cn"):
        self.username = username
        self.password = password
        self.server = server
        self.cookies: dict[str, str] = {}
        self.ssecurity: bytes = b""
        self.device_id = _random_string(16)
        self._client = httpx.Client(follow_redirects=True, timeout=15)
        self._logged_in = False
        self._auth_state: dict[str, Any] = {}

    def login(self) -> bool:
        if self._logged_in:
            return True
        try:
            r = self._client.get(
                "https://account.xiaomi.com/pass/serviceLogin",
                cookies={"sdkVersion": SDK_VERSION, "deviceId": self.device_id},
                params={"_json": "true", "sid": "xiaomiio"},
            )
            res1 = _parse_response(r.content)

            data = {
                "_json": "true",
                "sid": res1["sid"],
                "callback": res1["callback"],
                "_sign": res1["_sign"],
                "qs": res1["qs"],
                "user": self.username,
                "hash": hashlib.md5(self.password.encode()).hexdigest().upper(),
            }

            r = self._client.post(
                "https://account.xiaomi.com/pass/serviceLoginAuth2",
                cookies={"sdkVersion": SDK_VERSION, "deviceId": self.device_id},
                data=data,
            )
            res2 = _parse_response(r.content)

            notification_url = res2.get("notificationUrl", "")
            if notification_url:
                self._handle_notification(notification_url)
                return False

            if res2.get("code") != 0:
                raise RuntimeError(f"登录失败: {res2.get('desc', res2)}")

            return self._get_credentials(res2)

        except (VerificationRequired, RuntimeError):
            raise
        except Exception as e:
            self._logged_in = False
            raise RuntimeError(f"登录失败: {e}") from e

    def _handle_notification(self, notification_url: str):
        """处理二次验证通知"""
        identity_url = notification_url.replace(
            "/fe/service/identity/authStart", "/identity/list"
        )

        r = self._client.get(identity_url)
        res = _parse_response(r.content)

        flag = res.get("flag", 0)
        identity_session = ""
        for cookie in r.cookies.jar:
            if cookie.name == "identity_session":
                identity_session = cookie.value
                break

        key = "Phone" if flag == FLAG_PHONE else "Email"

        r = self._client.get(
            f"https://account.xiaomi.com/identity/auth/verify{key}",
            cookies={"identity_session": identity_session},
            params={"_flag": flag, "_json": "true"},
        )
        verify_res = _parse_response(r.content)

        r = self._client.post(
            f"https://account.xiaomi.com/identity/auth/send{key}Ticket",
            cookies={"identity_session": identity_session},
            data={"retry": 0, "icode": "", "_json": "true"},
        )
        _parse_response(r.content)

        self._auth_state = {
            "flag": flag,
            "identity_session": identity_session,
        }

        masked = verify_res.get(f"masked{key}", "***")
        raise VerificationRequired(masked, flag, identity_session)

    def submit_verification(self, code: str) -> bool:
        """提交验证码完成登录"""
        flag = self._auth_state.get("flag", FLAG_PHONE)
        identity_session = self._auth_state.get("identity_session", "")
        key = "Phone" if flag == FLAG_PHONE else "Email"

        r = self._client.post(
            f"https://account.xiaomi.com/identity/auth/verify{key}",
            cookies={"identity_session": identity_session},
            params={
                "_flag": flag,
                "ticket": code,
                "trust": "true",
                "_json": "true",
            },
        )
        res = _parse_response(r.content)

        if res.get("code") != 0:
            raise RuntimeError(f"验证码错误: {res.get('desc', res)}")

        return self._get_credentials(res)

    def _get_credentials(self, data: dict) -> bool:
        location = data.get("location", "")
        if not location:
            raise RuntimeError("登录响应缺少 location")

        r = self._client.get(location)

        self.cookies = {}
        for resp in [r] + list(r.history):
            for cookie in resp.cookies.jar:
                self.cookies[cookie.name] = cookie.value

        ssecurity = data.get("ssecurity", "")
        if not ssecurity:
            for resp in list(r.history):
                ext = resp.headers.get("extension-pragma", "")
                if ext:
                    ext_data = json.loads(ext)
                    ssecurity = ext_data.get("ssecurity", ssecurity)
                    data.update(ext_data)

        self.ssecurity = base64.b64decode(ssecurity)
        self._logged_in = True
        return True

    def get_devices(self) -> list[dict[str, Any]]:
        if not self._logged_in:
            self.login()
        payload = {
            "getVirtualModel": True,
            "getHuamiDevices": 1,
            "get_split_device": False,
            "support_smart_home": True,
        }
        result = self._request("/v2/home/device_list_page", payload)
        return result.get("list", [])

    def get_properties(self, params: list[dict]) -> list[dict]:
        """云端读取设备属性
        params: [{"did": "xxx", "siid": 2, "piid": 1}, ...]
        """
        if not self._logged_in:
            self.login()
        result = self._request("/miotspec/prop/get", {"params": params})
        return result if isinstance(result, list) else []

    def set_properties(self, params: list[dict]) -> list[dict]:
        """云端设置设备属性
        params: [{"did": "xxx", "siid": 2, "piid": 1, "value": true}, ...]
        """
        if not self._logged_in:
            self.login()
        result = self._request("/miotspec/prop/set", {"params": params})
        return result if isinstance(result, list) else []

    def call_action(self, did: str, siid: int, aiid: int, params: list | None = None) -> dict:
        """云端调用设备动作"""
        if not self._logged_in:
            self.login()
        payload = {"params": {"did": did, "siid": siid, "aiid": aiid, "in": params or []}}
        return self._request("/miotspec/action", payload)

    def get_homes_and_rooms(self) -> list[dict[str, Any]]:
        if not self._logged_in:
            self.login()
        payload = {"fg": True, "fetch_share": True, "limit": 300}
        result = self._request("/v2/homeroom/gethome", payload)
        return result.get("homelist", [])

    def _request(self, path: str, params: dict) -> dict:
        form: dict[str, str] = {"data": json.dumps(params, separators=(",", ":"))}

        nonce = _gen_nonce()
        signed_nonce = _gen_signed_nonce(self.ssecurity, nonce)

        form["rc4_hash__"] = _gen_signature(path, form, signed_nonce)

        for k, v in form.items():
            ciphertext = _crypt(signed_nonce, v.encode())
            form[k] = base64.b64encode(ciphertext).decode()

        form["signature"] = _gen_signature(path, form, signed_nonce)
        form["_nonce"] = base64.b64encode(nonce).decode()

        url = BASE_URLS.get(self.server, self.server) + path
        r = self._client.post(url, cookies=self.cookies, data=form)
        r.raise_for_status()

        ciphertext = base64.b64decode(r.content)
        plaintext = _crypt(signed_nonce, ciphertext)

        res = json.loads(plaintext)
        if res.get("code") != 0:
            raise RuntimeError(f"API 请求失败: {res}")
        return res.get("result", {})

    def close(self):
        self._client.close()


def _parse_response(body: bytes) -> dict:
    if body.startswith(b"&&&START&&&"):
        body = body[11:]
    return json.loads(body)


def _random_string(length: int) -> str:
    seq = string.ascii_uppercase + string.digits
    return "".join(random.choice(seq) for _ in range(length))


def _gen_nonce() -> bytes:
    return os.urandom(8) + int(time.time() / 60).to_bytes(4, "big")


def _gen_signed_nonce(ssecurity: bytes, nonce: bytes) -> bytes:
    return hashlib.sha256(ssecurity + nonce).digest()


def _gen_signature(path: str, data: dict, signed_nonce: bytes) -> str:
    params = ["POST", path]
    for k, v in data.items():
        params.append(f"{k}={v}")
    params.append(base64.b64encode(signed_nonce).decode())
    signature = "&".join(params)
    signature_hash = hashlib.sha1(signature.encode()).digest()
    return base64.b64encode(signature_hash).decode()


def _crypt(key: bytes, data: bytes) -> bytes:
    cipher = ciphers.Cipher(algorithms.ARC4(key), None)
    encryptor = cipher.encryptor()
    encryptor.update(bytes(1024))
    return encryptor.update(data)
