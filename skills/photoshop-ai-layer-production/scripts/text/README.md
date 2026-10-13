# 本地 OCR 与真文字层

默认路线不需要把图片上传到任何服务：

1. windows_ocr_tiles.ps1 用 Windows 自带 OCR 对超大图分块识别，输出坐标记录；
2. build_text_manifest_windows.py 去除重叠瓦片产生的重复项，并按目标文档尺寸与 DPI 生成 Photoshop 文字清单；
3. 用户或接收方 AI 校对 text、font、color_rgb、位置和低置信度项；
4. 用户在 Photoshop 打开目标 PSD/PSB 后，运行 add_editable_text_layers.ps1；
5. 脚本保存、关闭、重开并确认所有新增对象仍是文字层。

paddle_ocr_extract.py、scan_system_fonts.py 和 fit_text_fonts.py 是精细路线：PaddleOCR 保留多边形、置信度和字符框，字体扫描/拟合在本机字体库中找视觉近似。PaddleOCR 的程序与识别模型未随 Skill 打包，需要接收方按其官方安装说明建立独立环境。字体拟合表示“本机候选中最像”，不证明原字体元数据。
