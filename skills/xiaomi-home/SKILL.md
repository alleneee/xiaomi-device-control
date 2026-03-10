---
name: xiaomi-home
description: 小米/米家智能家居设备控制。通过 MCP Server 工具控制家中的小米设备，包括灯、空气净化器、电暖气、空调、风扇、扫地机器人、窗帘等。当用户提到任何关于智能家居控制的指令时触发，如"把灯关掉"、"开空调"、"净化器调到睡眠模式"、"客厅太暗了"、"家里空气不好"等。即使用户没有明确说"小米"或"米家"，只要涉及家居设备控制，都应该触发此 skill。也支持查询设备状态，如"空气质量怎么样"、"家里几度"等。
---

# 小米智能家居控制

你可以通过 MCP Server 提供的工具控制用户家中的小米/米家智能设备。

## 可用工具

MCP Server `xiaomi-home` 提供以下工具：

| 工具 | 用途 |
|------|------|
| `xiaomi_list_devices` | 列出所有设备，获取设备 did |
| `xiaomi_find_device` | 按名称模糊搜索设备 |
| `xiaomi_get_properties` | 读取设备属性 |
| `xiaomi_set_property` | 设置设备属性 |
| `xiaomi_call_action` | 调用设备动作 |

## 工作流程

### 第一步：定位设备

从用户的自然语言指令中提取设备关键词，用 `xiaomi_find_device` 搜索。

例如用户说"把客厅的灯关掉"，提取"客厅"或"灯"进行搜索。

如果没有找到，尝试用 `xiaomi_list_devices` 列出所有设备，让用户确认。

### 第二步：查询设备规格

拿到设备的 `model` 后，需要知道该设备支持哪些 siid/piid。

常见设备的 MIoT 规格：

**开关类设备（灯、插座、开关）**
- siid=2, piid=1: 开关 (bool)
- siid=2, piid=2: 亮度 (uint8, 1-100)
- siid=2, piid=3: 色温 (uint32)

**空气净化器**
- siid=2, piid=1: 开关 (bool)
- siid=2, piid=5: 模式 (uint8, 0=自动 1=睡眠 2=喜爱 3=手动)
- siid=2, piid=8: 风速等级
- siid=3, piid=6: PM2.5 (只读)
- siid=3, piid=8: 温度 (只读)
- siid=3, piid=7: 湿度 (只读)

**电暖气/取暖器**
- siid=2, piid=1: 开关 (bool)
- siid=2, piid=2: 目标温度
- siid=2, piid=3: 模式

**风扇**
- siid=2, piid=1: 开关 (bool)
- siid=2, piid=2: 风速等级
- siid=2, piid=3: 摆头 (bool)
- siid=2, piid=4: 模式

**扫地机器人**
- siid=2, piid=1: 状态
- siid=2, piid=2: 模式
- siid=2, aiid=1: 开始清扫（动作）
- siid=2, aiid=2: 停止清扫（动作）

以上仅为常见参考值，不同型号的 siid/piid 可能不同。如果控制失败，先用 `xiaomi_get_properties` 尝试读取 siid=2 的 piid 1-10 来探测设备支持的属性。

### 第三步：执行操作

根据用户意图调用对应工具：

- **开/关设备**: `xiaomi_set_property(did, siid=2, piid=1, value=true/false)`
- **调节属性**: `xiaomi_set_property(did, siid, piid, value)`
- **执行动作**: `xiaomi_call_action(did, siid, aiid)`
- **查询状态**: `xiaomi_get_properties(did, siid=2, piids="1,2,3,4,5")`

### 第四步：反馈结果

用自然语言告诉用户操作结果，例如：
- "已关闭客厅吸顶灯"
- "空气净化器已切换到睡眠模式，当前 PM2.5: 35"
- "电暖气已开启，目标温度设为 24 度"

如果操作失败，说明原因并建议排查方向（设备是否在线、是否在同一局域网等）。

## 场景联动

用户可能描述一个场景而非单个设备操作，例如：
- "我要睡觉了" → 关灯 + 净化器睡眠模式 + 电暖气调低
- "出门了" → 关闭所有设备
- "客厅太暗了" → 开灯并调高亮度

遇到场景指令时，拆解为多个设备操作，依次执行并汇报结果。

## 注意事项

- 操作前确认设备在线（is_online），离线设备无法控制
- siid/piid 因型号而异，失败时用探测方式确认正确的属性 ID
- 布尔值使用 true/false，不是 0/1
- 设备 did 是字符串，不要猜测，必须从 list 或 find 工具获取
