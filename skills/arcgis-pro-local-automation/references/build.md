# 对应源码与构建

`assets/addin-source/` 包含本版完整对应 C#、Config、嵌入参数/工具表、图标、项目文件、许可证及 NOTICE。没有 SDK、NuGet 缓存或 Esri DLL。构建要用接收方合法安装的 Pro SDK 程序集。

在该源码目录，Windows .NET 8 SDK 示例：

```powershell
dotnet build ArcGISProMCP.csproj -c Release -p:ProTargetVersion=3.4 -p:DeployAddIn=false -p:DebugType=None -p:DebugSymbols=false '-p:ArcGISProDir=D:/Apps/ArcGIS/Pro' '-p:PathMap=D:/public-build=/_/public-build'
```

把 `ArcGISProDir` 改成真正包含 `bin/ArcGISPro.exe` 的目录；示例不是固定安装路径。PathMap 左侧换成自己的源码根，不把真实用户路径保留到符号信息中。只在隔离源码副本中构建；不能对正在使用的插件或已安装 Esri 文件执行修补。

`DeployAddIn=false` 必须保留，构建不等于安装。生成的 `bin/Release/ArcGISProMCP.esriAddinX` 应只含 Config.daml 和 Install/ArcGISProMCP.dll，无 PDB、依赖缓存和 Esri 程序集。检查输出哈希和 DLL 内是否残留私有路径，再单独按接收方授权安装。不同构建环境不承诺逐字节复现；不要沿用旧包的哈希。

本版公开构建使用相同 47 个本地基线源码文件，另补齐上游 NOTICE/COMMERCIAL-LICENSE。只改变编译属性：Release、无调试符号、路径映射、不部署；没有改写业务 C# 逻辑。生成二进制与原实测包不同，本次没有实机加载验收。
