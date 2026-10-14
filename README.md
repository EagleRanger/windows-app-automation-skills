# Windows 办公软件自动化 Skill 合集与项目索引

集中下载办公软件控制、图册/报告、景观 PPT 和 Obsidian 配置。当前 **v1.1.0** 包含 **13 个可直接安装的独立 Skill**，并保留 1 个 Obsidian 安装附件。各工具继续按独立目录和自己的依赖运行；本主分支保留轻量目录与分发说明。

**[下载完整 Skill ZIP](https://github.com/EagleRanger/windows-app-automation-skills/releases/download/v1.1.0/windows-office-automation-skills-v1.1.0-20261014.zip)** · [查看本次发布](https://github.com/EagleRanger/windows-app-automation-skills/releases/tag/v1.1.0)

解压后运行 `powershell -ExecutionPolicy Bypass -File .\install.ps1 -All`，或只选择需要的 Skill。安装器复制 Skill，不自动覆盖不同的已有版本；软件本体、账号、Python 环境和其他依赖按各目录说明配置。

## 工具目录

| 项目 | Skill / 来源 | 分发 |
| --- | --- | --- |
| CAD / 天正图纸校审与标注 | [独立项目](https://github.com/EagleRanger/tianzheng-cad-automation-skills)，3 个 Skill | 随合集，也可从原项目下载 |
| GIS / ArcGIS Pro 控制 | [独立项目](https://github.com/EagleRanger/arcgis-pro-local-automation-skill)，1 个 Skill | 随合集，也可从原项目下载 |
| WPS 控制与报告排版 | [独立项目](https://github.com/EagleRanger/wps-local-automation-skills)，2 个 Skill | 随合集，也可从原项目下载 |
| Photoshop 控制与图层生产 | [独立项目](https://github.com/EagleRanger/photoshop-local-automation-skills)，3 个 Skill | 随合集，也可从原项目下载 |
| Chrome 受管浏览器 | [独立项目](https://github.com/EagleRanger/chrome-local-automation-skill)，1 个 Skill | 随合集，也可从原项目下载 |
| 建筑学长网页生图 | [独立项目](https://github.com/EagleRanger/jianzhuxuezhang-image-skill)，1 个 Skill | 随合集，也可从原项目下载 |
| **PPT Master 景观文本增强版** | [原项目](https://github.com/EagleRanger/ppt-master-landscape-text-enhanced)，`ppt-master` | **本合集内为截至 2026-10-13 的新快照**；原独立 Release 的日期/版本可能较早 |
| **图册与报告范本复刻** | `report-template-replication`，1 个自包含 Skill | **本次随合集首次分发，可单独安装此目录** |
| Obsidian 本地知识库 | [独立项目](https://github.com/EagleRanger/obsidian-vault-setup) | 独立原发布 ZIP 随包附带，按其说明安装 |

图册与 PPT 都已直接放入 ZIP 的 `skills/` 下；不用再从附件拆第二层 PPT 包。CAD 公开框架不包含完整私有执行器。新机器的实际软件连接、字体与渲染仍需接收方验证。

## 本次范围

合集不再包含签到、模型桥接/额度补丁、金融或游戏自动化。通用 PPT 图标和图表模板可以有金融/游戏题材的文件名，它们仅为可选制图素材，不是相应自动化程序。真实项目文件、业务数据库、账号和凭据不随包公开。

机器可读清单见 [catalog.json](catalog.json)，包内另附各 Skill 指纹和 SHA-256。历史版本说明见 [HISTORICAL_RELEASES.md](HISTORICAL_RELEASES.md)。

## 来源与支持

保留 [分项许可](LICENSES.md) 和 [第三方来源](THIRD_PARTY_NOTICES.md)。PPT Master 基于 Hugo He 的 MIT 项目，Theme Factory 资料保留 Apache-2.0；其他组件沿用各自声明。

如果实际下载、使用或借鉴后觉得对开发有帮助，欢迎自愿给对应项目 Star。EagleRanger 提出需求与验收，OpenAI Codex 协助整理、打包和核验。
