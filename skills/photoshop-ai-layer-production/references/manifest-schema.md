# 生产清单格式

为每个真实生产任务建立一份 JSON 清单。字段可以扩展，但不要删除身份、授权和验收边界。

```json
{
  "schema": "photoshop_ai_layer_production_v1",
  "run_id": "PS-AI-LAYER-YYYYMMDD-001",
  "status": "prepared",
  "source": {
    "path": "C:/absolute/source.png",
    "sha256": "...",
    "width": 10000,
    "height": 7000,
    "mode": "RGB",
    "dpi": [300, 300]
  },
  "output": {
    "path": "C:/absolute/output.psb",
    "format": "PSB",
    "overwrite_authorized": false
  },
  "permissions": {
    "external_upload": false,
    "save": true,
    "close_target": true,
    "restart_photoshop": false
  },
  "assets": [
    {
      "path": "assets/01_source_pixels.png",
      "name": "原像素未遮挡区",
      "role": "source_pixels",
      "inferred": false,
      "alpha_required": true,
      "sha256": "..."
    },
    {
      "path": "assets/02_ai_completion.png",
      "name": "AI补全_非测绘依据",
      "role": "ai_completion",
      "inferred": true,
      "alpha_required": true,
      "sha256": "..."
    }
  ],
  "acceptance": {
    "connected": false,
    "readable": false,
    "written": false,
    "saved": false,
    "reopened": false,
    "visually_accepted": false,
    "source_unchanged": false,
    "editable_text_layers": null,
    "unresolved_visual_risks": []
  }
}
```

## 状态规则

- `prepared`：源图、输出和资产已冻结，但未写入 Photoshop。
- `written`：预期图层或像素已在目标文档观察到，但不表示已保存。
- `saved`：授权路径存在且保存状态成立，但未证明重开结构。
- `reopened`：保存后关闭重开，结构验收通过。
- `accepted`：重开、源文件未变化及必要视觉验收均通过。
- `failed`、`interrupted`、`unknown`：如实记录；超时或缺少回执不得标成成功。

`scripts/validate_production_manifest.py` 验证路径、哈希、画布、资产角色、透明通道和授权矛盾。它不能读取 Photoshop 图层语义，也不能替代重开或视觉验收。
