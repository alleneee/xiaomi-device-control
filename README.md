# xiaomi-device-control

小米/米家智能家居 Claude Code Plugin，通过自然语言控制米家设备。

## 功能

- 列出所有米家设备
- 根据名称搜索设备
- 云端读取设备属性（开关状态、温度、PM2.5等）
- 云端设置设备属性（开关、亮度、模式等）
- 云端调用设备动作（开始清扫等）
- 自然语言场景联动（"我要睡觉了" -> 多设备操作）

## 架构

```text
                Claude Code
                    |
    +---------------+---------------+
    |                               |
  Skill                        MCP Server
  (自然语言 -> 设备操作)        (5 个工具)
                                    |
                             小米云端 API
                            (MIoT 协议)
                                    |
                              米家设备
```

- **MCP Server**: 底层连接层，提供 5 个标准化工具，通过小米云端 API 控制设备
- **Skill**: 上层智能层，将自然语言指令映射为设备操作流程
- **Plugin**: 打包层，一键安装 MCP + Skill

## 安装

### 方式一：Claude Plugin（推荐）

在 Claude Code 交互界面中执行：

```text
/plugin marketplace add alleneee/xiaomi-device-control
/plugin install xiaomi-home@alleneee-xiaomi-device-control
```

或在命令行中执行：

```bash
claude plugin marketplace add alleneee/xiaomi-device-control
claude plugin install xiaomi-home@alleneee-xiaomi-device-control
```

### 方式二：手动安装

```bash
git clone <repo-url>
cd xiaomi-device-control
uv sync
```

在 `~/.claude/settings.json` 的 `mcpServers` 中添加：

```json
{
  "xiaomi-home": {
    "command": "uv",
    "args": ["run", "--directory", "/path/to/xiaomi-device-control", "python", "-m", "src.server"],
    "env": {
      "MI_USERNAME": "你的小米账号",
      "MI_PASSWORD": "你的密码",
      "MI_CLOUD_COUNTRY": "cn"
    }
  }
}
```

复制 `skills/xiaomi-home/` 到 `~/.claude/skills/xiaomi-home/`。

## 配置

### 1. 设置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```text
MI_USERNAME=你的小米账号
MI_PASSWORD=你的密码
MI_CLOUD_COUNTRY=cn
```

### 2. 首次登录认证

小米账号需要二次验证，首次使用需手动完成：

```bash
uv run python -m src.auth_helper
```

收到验证码后：

```bash
uv run python -m src.auth_helper verify <验证码>
```

认证成功后会保存 token 到 `.mi_token`，后续无需重复验证。

## 可用工具

| 工具 | 说明 |
|------|------|
| `xiaomi_list_devices` | 列出所有设备 |
| `xiaomi_find_device` | 根据名称搜索设备 |
| `xiaomi_get_properties` | 云端读取设备属性 |
| `xiaomi_set_property` | 云端设置设备属性 |
| `xiaomi_call_action` | 云端调用设备动作 |

## MIoT 协议说明

设备属性通过 `siid`(服务ID) 和 `piid`(属性ID) 定位，查询设备规格：<https://home.miot-spec.com>

常见组合：

- 开关：`siid=2, piid=1`（true/false）
- 亮度：`siid=2, piid=2`（0-100）
- 色温：`siid=2, piid=3`
- 空气净化器模式：`siid=2, piid=5`
- PM2.5：`siid=3, piid=6`

## 项目结构

```text
xiaomi-device-control/
├── .claude-plugin/
│   └── marketplace.json       # 插件市场清单
├── plugins/
│   └── xiaomi-home/           # 插件目录
│       ├── .claude-plugin/
│       │   └── plugin.json    # 插件元数据
│       ├── .mcp.json          # MCP Server 声明
│       └── skills/
│           └── xiaomi-home/
│               └── SKILL.md   # Skill 定义
├── skills/
│   └── xiaomi-home/
│       └── SKILL.md           # Skill 定义（手动安装用）
├── src/                       # MCP Server 源码
│   ├── server.py              # FastMCP Server（5个工具）
│   ├── xiaomi_client.py       # 设备操作封装
│   ├── micloud.py             # 小米云端 API 客户端
│   ├── auth_helper.py         # 认证辅助（二次验证）
│   └── config.py              # 配置管理
├── .env.example
├── pyproject.toml
└── README.md
```

## 使用示例

```text
用户: 把电暖器打开
Claude: 搜索设备 -> 找到电暖器 did -> 设置 siid=2, piid=1, value=true -> "已开启米家石墨烯智能电暖器"

用户: 空气质量怎么样
Claude: 搜索净化器 -> 读取 PM2.5 -> "当前 PM2.5: 46，空气质量良好"

用户: 我要睡觉了
Claude: 关灯 + 净化器切睡眠模式 + 电暖器调低温度 -> 逐一汇报结果
```

## 许可证

MIT
