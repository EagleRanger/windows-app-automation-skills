# 离线检查

这些测试验证包装与局部安全规则，不代表接收方电脑已连接真实软件。

`test_wps_session_admission.py` 来自已验 WPS 后端的回归测试。将
`skills/wps-report-workflow/vendor/wps-cli/src` 加到 `PYTHONPATH`，使用装有
pytest 和 pywin32 的 Windows Python，运行：

```powershell
python -m pytest -q -p no:cacheprovider .\tests\test_wps_session_admission.py
```

9 个用例将 COM DispatchEx 全部替换为 mock，不启动 WPS。检查三个组件
拒绝有文档/可见的外来会话，并接纳空的隐藏会话。

Photoshop 包内容检查与纯文件烟测：

```powershell
python .\skills\photoshop-ai-layer-production\scripts\verify_bundle.py
python .\skills\photoshop-ai-layer-production\tests\smoke_test.py
```

后者需要 Pillow/numpy 等本地依赖，只处理临时示例图，不调用 Photoshop、
ComfyUI、模型接口或下载权重。全库安装器可在指定的空测试目录重复运行，
不要用真实 Skill 安装目录做冲突测试。
