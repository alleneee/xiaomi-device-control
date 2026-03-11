import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.auth_helper import get_auth_status, initiate_login, submit_verification
from src.xiaomi_client import (
    call_device_action,
    find_device_by_name,
    get_device_properties,
    list_devices,
    set_device_property,
)

mcp = FastMCP("xiaomi-home")


@mcp.tool()
def xiaomi_auth_status() -> str:
    """检查小米账号认证状态。首次使用时调用此工具确认是否需要配置。"""
    result = get_auth_status()
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_setup(username: str, password: str, country: str = "cn") -> str:
    """配置小米账号并发起登录。首次使用或需要重新认证时调用。

    参数:
        username: 小米账号（手机号或邮箱）
        password: 小米账号密码
        country: 服务器区域，默认 cn（中国大陆），可选 de/i2/ru/sg/us
    """
    result = initiate_login(username, password, country)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_verify(code: str) -> str:
    """提交小米二次验证码。在 xiaomi_setup 提示需要验证后调用。

    参数:
        code: 手机或邮箱收到的验证码
    """
    result = submit_verification(code)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_list_devices() -> str:
    """列出所有小米/米家智能家居设备，返回设备ID(did)、名称、型号、在线状态。
    这是操作设备的第一步，用于获取设备的 did。"""
    devices = list_devices()
    return json.dumps(devices, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_find_device(name: str) -> str:
    """根据名称模糊搜索小米/米家设备。

    参数:
        name: 设备名称关键词，如"客厅"、"净化器"、"卧室"
    """
    devices = find_device_by_name(name)
    if not devices:
        return json.dumps({"message": f"未找到包含 '{name}' 的设备"}, ensure_ascii=False)
    return json.dumps(devices, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_get_properties(did: str, siid: int, piids: str) -> str:
    """读取设备属性。使用 MIoT 协议的 siid(服务ID) 和 piid(属性ID)。
    常见 siid-piid 组合:
    - 开关类: siid=2, piid=1 (on/off)
    - 空气净化器: siid=2, piid=1(开关), piid=5(模式); siid=3, piid=6(PM2.5)
    - 灯: siid=2, piid=1(开关), piid=2(亮度), piid=3(色温)
    具体设备的 siid/piid 可查询 https://home.miot-spec.com

    参数:
        did: 设备ID
        siid: 服务ID
        piids: 属性ID列表，逗号分隔，如 "1,2,3"
    """
    piid_list = [int(p.strip()) for p in piids.split(",")]
    result = get_device_properties(did, siid, piid_list)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_set_property(did: str, siid: int, piid: int, value: Any) -> str:
    """设置设备属性值。
    常见操作:
    - 开/关设备: siid=2, piid=1, value=true/false
    - 设置亮度: siid=2, piid=2, value=50
    - 设置模式: siid=2, piid=5, value=0(自动)/1(睡眠)/2(喜爱)

    参数:
        did: 设备ID
        siid: 服务ID
        piid: 属性ID
        value: 属性值（布尔、整数、字符串等）
    """
    result = set_device_property(did, siid, piid, value)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def xiaomi_call_action(did: str, siid: int, aiid: int, params: str = "") -> str:
    """调用设备动作（非属性设置类操作），如扫地机开始清扫、空气净化器重置滤芯。

    参数:
        did: 设备ID
        siid: 服务ID
        aiid: 动作ID
        params: JSON 格式的参数列表，如 '[1, "test"]'，无参数留空
    """
    param_list = json.loads(params) if params else []
    result = call_device_action(did, siid, aiid, param_list)
    return json.dumps(result, ensure_ascii=False, indent=2)
