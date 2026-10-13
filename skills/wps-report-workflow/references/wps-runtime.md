# 本地 WPS 运行与边界

## 依赖与部署

需要 Windows、桌面 WPS（可正常手动打开 Word）、PowerShell 7 和 Python 3.10+。Python 文件处理按需使用 lxml、python-docx、pypdfium2/Pillow 或已有等效工具。两项随附校验器只需 Python 标准库；Skill 本身不是 WPS 安装器或授权许可证。

优先复用现有隔离环境。随附 `vendor/wps-cli` 是当时本机兼容补丁后的源码快照，包含原许可证；不要盲换为同名在线最新版。新电脑可在用户允许安装依赖后，将其装入专用虚拟环境：

```powershell
# $pythonExe 为已确认的 Python 路径；$skillPath 为本 Skill 绝对路径。
# $bridgeRoot 为新建或已明确允许使用的专用环境目录，不覆盖现有环境。
& $pythonExe -m venv "$bridgeRoot\.venv"
& "$bridgeRoot\.venv\Scripts\python.exe" -m pip install "$skillPath\vendor\wps-cli"
$env:WPS_LOCAL_AI_HOME = $bridgeRoot
```

上述安装会在缺少依赖时访问包源，不能把它说成离线安装。没有用户安装许可时只说明缺口；不能自动修改 COM 注册、WPS 安装或启用云端功能。

本合集的两个 WPS Skill 使用相同的已验生产包装器。设置 `WPS_LOCAL_AI_HOME` 指向含 `.venv/Scripts/wps.exe` 的目录；未设置时明确停止，不猜发布者路径。`wps-local-sync` 也使用这同一环境。首次在新机运行，先用自建小样测试，再使用正式文件。

## 本报告任务使用的路径

编辑 DOCX 文件结构及文字 → WPS 重开 → 导出 PDF → 页面渲染与视觉检查 → 最终路径重开读回。

```powershell
$bridge = Join-Path $skillPath 'scripts\invoke_wps_cli.ps1'
& $bridge -CommandArgs @('writer','info',$docxPath,'--json')
& $bridge -CommandArgs @('writer','track-changes-get',$docxPath,'--json')
& $bridge -CommandArgs @('writer','validate',$docxPath,'--json')
& $bridge -CommandArgs @('writer','export-pdf',$docxPath,'--output',$pdfPath,'--json') -TimeoutSeconds 300
```

路径必须指向本次已确认文件；输出不存在或允许覆盖，命令数组逐参数传递。不要把“success=true”当成已保存或正确，仍需新文件指纹、重新打开和可见结果。

## 保护用户窗口

- 后端通过 DispatchEx 获取对象后，先检查实际返回会话是否已有文档或可见窗口；不符合准入则报 WPS_FOREIGN_SESSION，保持原会话不动。`-AllowVisibleWps` 不会绕过保护。
- 包装器按组件和绝对输入/输出路径租约。不同组件、独立路径可以按已验边界重叠；同组件 legacy 调用仍串行。不会按新 PID 差集结束 WPS，超时只终止其拥有的 CLI。详见同包 `wps-local-sync/references/parallel_sessions.md`。
- 新机或权限变化后，窗口/进程读取失败视为未知而不是“没有窗口”。先恢复可判断的运行上下文，不绕过保护。
- 有可用且获授权的桌面控制能力时，UI 操作须新截图确认目标及弹窗，单步操作再读回；不能盲点保存/覆盖/兼容/宏弹窗。当前宿主没有桌面控制能力就明确告知，不假装已点击。
- 超时先核对文件与进程实际状态，再决定是否重试。只清理本次可确认拥有的进程，不全局结束 WPS。

## 已验证与已失败分开

历史宿主为 WPS 12.1.0.28043。此环境真实使用过 Writer 重开/信息读取/验证/导出，以及段落、批注、修订状态等部分适配器；并不证明其他 WPS 版本、所有命令或整个对象模型可靠。

- `writer replace`、`writer merge`、`writer table-insert` 曾返回成功但重开未持久化或插入位置不明确；包装器直调及 Writer 对应批量调用已隔离，使用文件级编辑后再 WPS 验证。
- 原生 PDF 后台修改可能弹出可见阅读器；不经批量或任意 COM 绕过限制。PDF 合并/页面操作优先现有文件工具。
- PDF 转可编辑 Word 没有在本包中封装成熟的静默适配器。用户指定 WPS 时优先其对应转换功能或用户提供的转换稿，先小样核对；不得用整页截图替代全文可编辑要求。
- WPS 365、灵犀、AI 转换和会员能力不是本地 COM 的同一权限域；不得自动上传材料或使用未经验证的私有接口。
- 受限宿主进程可能读不到实际用户 COM 注册；先在合适且获允许的用户上下文做最小只读验证，不凭一次失败反复注册/修复。

本 Skill 以 Word 报告为范围。源码包含其他格式命令，不因此授予对表格、演示或系统配置的操作权限。
