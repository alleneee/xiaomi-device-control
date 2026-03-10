from __future__ import annotations

import logging
from typing import Any

from src.auth_helper import load_cloud_from_token
from src.config import get_settings
from src.micloud import MiCloud

logger = logging.getLogger(__name__)


class DeviceCache:
    """缓存云端设备列表"""

    def __init__(self):
        self._cloud: MiCloud | None = None
        self._cloud_devices: list[dict[str, Any]] = []
        self._device_map: dict[str, dict[str, Any]] = {}

    @property
    def cloud(self) -> MiCloud:
        if self._cloud is None:
            self._cloud = load_cloud_from_token()
            if self._cloud is None:
                s = get_settings()
                self._cloud = MiCloud(
                    username=s.mi_username,
                    password=s.mi_password,
                    server=s.mi_cloud_country,
                )
        return self._cloud

    def get_cloud_devices(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        if not self._cloud_devices or force_refresh:
            self._cloud_devices = self.cloud.get_devices()
            self._device_map = {d["did"]: d for d in self._cloud_devices}
        return self._cloud_devices


cache = DeviceCache()


def list_devices() -> list[dict[str, Any]]:
    """列出所有米家设备"""
    devices = cache.get_cloud_devices()
    result = []
    for dev in devices:
        result.append({
            "did": dev.get("did", ""),
            "name": dev.get("name", ""),
            "model": dev.get("model", ""),
            "ip": dev.get("localip", ""),
            "is_online": dev.get("isOnline", False),
        })
    return result


def get_device_properties(did: str, siid: int, piids: list[int]) -> dict[str, Any]:
    """通过云端 API 读取设备属性"""
    try:
        params = [{"did": did, "siid": siid, "piid": piid} for piid in piids]
        results = cache.cloud.get_properties(params)
        return {"did": did, "properties": results}
    except Exception as e:
        return {"error": f"获取属性失败: {e}"}


def set_device_property(did: str, siid: int, piid: int, value: Any) -> dict[str, Any]:
    """通过云端 API 设置设备属性"""
    try:
        params = [{"did": did, "siid": siid, "piid": piid, "value": value}]
        results = cache.cloud.set_properties(params)
        return {"success": True, "did": did, "siid": siid, "piid": piid, "value": value, "result": results}
    except Exception as e:
        return {"error": f"设置属性失败: {e}"}


def call_device_action(did: str, siid: int, aiid: int, params: list[Any] | None = None) -> dict[str, Any]:
    """通过云端 API 调用设备动作"""
    try:
        result = cache.cloud.call_action(did, siid, aiid, params)
        return {"success": True, "did": did, "siid": siid, "aiid": aiid, "result": result}
    except Exception as e:
        return {"error": f"执行动作失败: {e}"}


def find_device_by_name(name: str) -> list[dict[str, Any]]:
    """根据名称模糊搜索设备"""
    devices = cache.get_cloud_devices()
    result = []
    for dev in devices:
        dev_name = dev.get("name", "")
        if name.lower() in dev_name.lower():
            result.append({
                "did": dev.get("did", ""),
                "name": dev_name,
                "model": dev.get("model", ""),
                "ip": dev.get("localip", ""),
                "is_online": dev.get("isOnline", False),
            })
    return result
