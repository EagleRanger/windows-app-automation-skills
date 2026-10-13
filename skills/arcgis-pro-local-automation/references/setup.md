# 接收方连接与配置

## 前置条件

本版基线：Windows x64、ArcGIS Pro 3.4.3、其正常可用的本地许可。TCP 客户端可用 Python 3.10+ 标准库执行；ArcPy 需要 Pro 自带 Python 环境，普通系统 Python 不能替代。构建插件另需 .NET 8 SDK；运行插件不要求接收方自行编译。

Skill 安装和 AddIn 安装是两件事。先查看 Pro 的 About/版本与 Add-In Manager；若已有同类插件，先检查 GUID 和版本，避免重复控制。不要把旧包直接覆盖到用户正在运行的目录。

## AddIn 安装

在用户确认插件安装后，以 Pro 的正常 AddIn 安装入口打开 `assets/ArcGISProMCP.esriAddinX`，确认来源并安装。本插件未签名；如果组织策略禁用未签名 AddIn，应由管理员处理，不绕过策略。用户保存自己的工作后正常重启 Pro，在 Add-In Manager 查看插件是否加载。不要替用户强杀进程或自动覆盖已安装插件。

包内版本：Config.daml 1.1.4，目标 Pro 3.4，.NET 8。程序集旧 Version 字段 1.1.1 是原源码遗留元数据，不是另一个控制实现。新公开二进制需要接收方按下述步骤验收。

## 连接顺序

插件启动后在 `%LOCALAPPDATA%/ArcGIS-MCP/instances/` 写实例 JSON。TCP 与 HTTP MCP 仅绑定 loopback；不要开放远程网络端口，不要转发到公网。本地桥没有用户认证，loopback 不是隔离不可信本机程序的安全沙箱。

从 Skill 目录执行（`python` 换成接收方实际 Python）：

```powershell
python scripts/bridge_client.py --help
python scripts/bridge_client.py --discover
python scripts/bridge_client.py --schema get_project_info
```

发现记录仅是候选；旧进程退出可能留下记录。客户端需以实际 `ping` 验证 PID；多实例时明确选端口和 PID，不猜“最近一个”。使用 `--port`、`--pid` 指定所选实例，`--command get_project_info` 获取新鲜工程身份，再把绝对 APRX 路径用作后续 `--expected-project`。参数的最终用法以 `--help` 为准。

写入同时要求 `--allow-write`、`--expected-project` 和独占新 `--receipt`，文件输出另用 `--output-root` 限定。授权范围须由对话确认；开关本身不等于用户批准。先在测试副本中做一次新文件导出，再核对输出与工程。不要把真实本机实例 JSON 或审计回执提交 GitHub。

HTTP MCP 是可选连接通道，不是必需再装的 Python 服务。实际地址从新鲜 `ping` 的 `mcp_url` 获取；不能固定抄用发布者端口。协议及工具清单由 AddIn 提供，前端连接配置按接收方已有 MCP 客户端支持方式设置；不修改其无关模型/账号配置。

已知问题仅简记在 [我们已踩过的坑](known-pitfalls.md)；不另附排障教程，新 bug 由接收方自行处理。
