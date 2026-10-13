# Windows 多软件自动化对接合集

把已有的软件对接 Skill 和已发布版本集中分类，方便自己的其他 Windows 电脑一次下载带走。这里是迁移合集，不是把软件、账号、许可、模型权重也一键装好。

## 一次下载与安装

下载本仓库 Release 的完整 ZIP 并解压，在根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -All
```

将 `skills/` 下 11 个 Skill 安装到当前用户 `.codex/skills`；可用 `-Destination` 指定目录。相同内容重复安装不变，不同内容拒绝覆盖。`-WhatIf` 只预览。安装器不启动软件、不登录、不下载大模型、不修改现有 Codex 插件或程序。

`existing-releases/` 已附带下表五个既有项目的完整发布 ZIP，无需再逐仓库下载。它们有各自的安装方式，特别是 Codex 补丁不得被普通 Skill 复制动作自动应用。版本、来源、SHA-256 见 `existing-releases/catalog.json`；原仓库仍是后续更新入口。

## 分类

| 分类 | 内置 Skill / 既有版本附件 |
| --- | --- |
| CAD / 天正 | cad-check-review、tianzheng-batch-polyline-dimension、tianzheng-cad-automation-framework |
| WPS / 报告 | wps-local-sync、wps-report-workflow；含当前已验后端与一致包装器 |
| Photoshop | photoshop-local-automation、photoshop-ai-layer-production、photoshop-raster-to-layered-psb |
| GIS | arcgis-pro-local-automation；只含自动化控制，不含三套地形配色方案 |
| 浏览器 / 建筑学长 | chrome-local-automation、jianzhuxuezhang-image |
| PPT 景观文本增强版 | [ppt-master-landscape-text-enhanced](https://github.com/EagleRanger/ppt-master-landscape-text-enhanced) v1.1.0 完整附件 |
| WorkBuddy 签到 | [wb-daily-checkin](https://github.com/EagleRanger/wb-daily-checkin) v2.0.0；坐标需按本机窗口与分辨率校准 |
| Obsidian 知识库 | [obsidian-vault-setup](https://github.com/EagleRanger/obsidian-vault-setup) 已发布安装附件 |
| Codex 多模型 / 额度栏 | [codex-multimodel-quota-bridge](https://github.com/EagleRanger/codex-multimodel-quota-bridge) v2.1.0；自己的凭据另配 |
| 方舟自动化 | [maa-arknights-ai-automation](https://github.com/EagleRanger/maa-arknights-ai-automation) v0.4.0；不含私人执行器或账号 |
| 项目管理方法（索引，不内置） | [codex-project-reasoning-loop](https://github.com/EagleRanger/codex-project-reasoning-loop) |

CAD 框架已并入此合集，不另建重复仓库。它体现全套天正图纸的分层框架和已有模块，但不是“安装后全图纸自动生成”：私有驱动/兼容项目 checkout 不分发，批量标注仍需接收方的兼容执行器。

## 运行条件与边界

- 接收方自行合法安装相关软件；各 Skill 保留版本和实测边界。安装文件不等于新电脑连接或业务验收通过。
- WPS 桥可从随包 `wps-report-workflow/vendor/wps-cli` 安装到自己的隔离环境，两个 WPS Skill 统一设置 `WPS_LOCAL_AI_HOME`。依赖安装可能联网；本合集安装器只复制 Skill。
- 浏览器对接依赖宿主受管 tab，登录/验证码由接收方完成；不是通用独立 CDP 服务。
- 大模型从各自明确来源另行下载/校验，不内置。原地图、公司工程、图纸、私人日志、截图、缓存和认证值不进入本合集。
- 已踩过的坑保留简记；新环境和新 bug 由接收方定位。原软件功能实测、此次迁移测试、接收方真实运行分开陈述。

## 来源与许可

见 [分项许可](LICENSES.md) 和 [第三方来源](THIRD_PARTY_NOTICES.md)。保留原组件许可证，不增加全库统一授权。EagleRanger 提出需求与验收，OpenAI Codex 协助整理与校审。
