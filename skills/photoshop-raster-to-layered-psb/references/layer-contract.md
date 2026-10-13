# Layer and acceptance contract

## Recommended root structure

- 可编辑文字_OCR字体拟合_默认隐藏
  - 标题
  - 图例
  - 地图标注
  - 编号
  - 比例尺与指北针
- 上层可编辑元素
  - 默认原图校准_编辑上层时隐藏
  - 图例与指北针_原像素
  - 标题栏_原像素
  - 边界与标记_原像素
  - 项目范围蒙版_原像素
- 底图_修复完成
  - AI补全_非测绘依据
  - 原像素未遮挡区
  - 白色画布
- 原图参考_锁定

Adapt names to the document, but preserve the distinction between source pixels, inferred repair, editable objects, default calibration, and locked reference.

## Pixel rules

- The default calibration view should reproduce the source exactly at a common render size. Compare decoded pixel arrays, not only file hashes, because JPEG metadata may differ.
- Source-native layers should use a source duplicate plus a mask. The mask may be generated from an RGBA asset, but the visible RGB values should come from the source document.
- AI completion must be confined to areas not evidenced by the original. Never allow a generated clean plate to replace unchanged map or plan pixels without disclosure.
- Closing all upper elements should reveal a continuous background. Inspect text, thin lines, high-contrast edges, former icon locations, and mask borders at useful zoom.

## Save and batch rules

- Save a new output and reopen it before acceptance.
- Record document size, dimensions, DPI, root and subgroup counts, layer types, mask presence, group visibility, saved state, hashes, and unresolved visual risks.
- A batch recipe is frozen only after the pilot passes. Run one source at a time through the same live Photoshop instance and output path.
