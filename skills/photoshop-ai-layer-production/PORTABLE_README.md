# 搬运与复现说明

## 交付边界

这个目录就是完整 Skill 源。它包含生产逻辑、固定版本、下载位置、哈希、工作流、Photoshop 写入、OCR/文字工具与验收模板。为节约空间，不内置三份 Qwen 权重；首次搭建时由脚本从官方 Hugging Face 仓库下载约 30.2GB，并逐份校验。

“复制完成”不等于“可运行”。新机器至少需要：

- Windows 10/11 x64；
- NVIDIA GPU，建议 16GB 以上显存；FP8 路线在 RTX 4080 16GB 上实测通过；
- 与显卡驱动匹配的 CUDA 版 PyTorch；本机实测为 Python 3.12.14、PyTorch 2.11.0+cu126、驱动 560.94；
- Photoshop 2021 或兼容的 Windows COM 自动化版本，由用户自己打开目标原图；
- 下载模型时可访问 Hugging Face；推断和图像处理均在本机进行。

## 一键入口

在 PowerShell 中，从 Skill 根目录执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1 -RuntimeRoot D:\PS-AI-Runtime -DownloadModels
```

脚本会：

1. 克隆 `config/runtime-lock.json` 固定的 ComfyUI 提交；
2. 创建 Python 虚拟环境；
3. 安装固定依赖，并使用 CUDA 12.6 的 PyTorch 索引；
4. 下载三份模型到正确目录，支持断点续传；
5. 运行静态与文件哈希检查。

若接收方已有 ComfyUI，可只下载模型：

```powershell
.\scripts\download_models.ps1 -ComfyRoot D:\ComfyUI
```

若只想检查，不下载：

```powershell
python .\scripts\check_environment.py --comfy-root D:\ComfyUI
```

## 运行一张图

1. 启动 ComfyUI：

```powershell
.\scripts\start_comfyui.ps1 -RuntimeRoot D:\PS-AI-Runtime
```

2. 调用本地 API：

```powershell
D:\PS-AI-Runtime\venv\Scripts\python.exe .\scripts\run_qwen_layered.py `
  --comfy-root D:\PS-AI-Runtime\ComfyUI `
  --input C:\work\source.png `
  --output-dir C:\work\qwen_layers `
  --prompt "Describe the complete image and obscured background." `
  --layers 8
```

3. 生成接触表并复合校验：

```powershell
D:\PS-AI-Runtime\venv\Scripts\python.exe .\scripts\make_contact_sheet.py `
  C:\work\qwen_layers C:\work\contact.jpg
```

4. 复制 `examples/layer-map.example.json`，按该图真实层序填写；再生成原尺寸资产：

```powershell
D:\PS-AI-Runtime\venv\Scripts\python.exe .\scripts\restore_original_size_layers.py `
  --source C:\work\source.png `
  --layers-dir C:\work\qwen_layers `
  --mapping C:\work\layer-map.json `
  --output-dir C:\work\full_layers
```

5. 复制 `examples/job.example.json`，改成绝对路径。由用户在 Photoshop 打开源图后执行：

```powershell
.\scripts\assemble_photoshop_document.ps1 -JobJson C:\work\job.json
```

## 真实性说明

- Qwen 输出顺序只有批次顺序，没有语义名或 z-index。每张图必须看接触表后映射。
- `original_rgb_masked` 只保留原图可见区域的 RGB，不能恢复被遮挡像素。
- `ai_rgba` 可补全被遮挡背景，但属于 AI 推断，不是测绘或历史真值。
- Photoshop 组装必须在新路径保存；脚本拒绝覆盖任何已有文件。
