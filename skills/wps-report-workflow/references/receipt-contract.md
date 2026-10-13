# 既有RA-v4回执检查器契约

随附只读检查器保留RA-20260905-v4，不是排版器、内容识别器或强制系统钩子。复杂批量可显式使用；已有等效项目检查不再复制。业务回执和真实证据留在业务目录，不把它们写进Skill。

```text
python <skill目录>/scripts/check_release_receipt.py <回执.json> --stage batch
python <skill目录>/scripts/check_release_receipt.py <回执.json> --stage delivery
python -B <skill目录>/scripts/test_release_receipt.py
```

测试在临时目录用合成记录验证拒绝行为，不证明真实文档排版。非零退出时诊断相关证据缺口；不要为过门倒填pass或改验收标准。

## 字段

文件引用均为本地绝对路径及实际SHA256：`{path, sha256}`。检查器拒绝UNC形式；网络文件需先按授权制作可验证本地副本，不能擅自搬移源件。所有“已检查”布尔值只写真实观察。

- `policy_version`：RA-20260905-v4；`method_id`：本次模板/方法版本；`open_findings`：无未决项才为空数组。
- `artifact`：候选文件引用；`snapshot`：文件引用加`input_sha256`、`page_count`、`renderer`，输入指纹匹配候选。
- `sources`：已有来源清单文件引用，内含最新要求、对象权威/保护范围、模板参数和版本；检查器只验此清单文件指纹，不读取/验证所有内部来源或语义映射。
- `reviewer`：`{identity, mode}`，mode为`self_review`或`independent_review`。实际模型及档位在证据中如实记载；检查器不判断是否真的独立。
- `checks`每项：`{status, evidence:{path,sha256}}`。batch需要`source_scope`、`editability`、`geometry`、`protected_content`、`preview_fidelity`；delivery另需`content_inventory`、`toc_pagination`、`reference_fidelity`、`cross_object_consistency`、`reopen`。
- 检查默认status为pass；仅`toc_pagination`、`reference_fidelity`、`cross_object_consistency`可按真实范围为`not_applicable`，另附`reason`与依据。用户要求范本复刻时不能豁免reference_fidelity。
- `samples`：`required_types`、`passed_types`为本次实际页型集合，`evidence`指向逐类小样记录；两集合相同不能自行证明小样选择充分。
- delivery的`materials`：`expected_ids`来自独立源清单；`items`每项含`id`、`disposition`、`source_checked`、`first_checked`、`last_checked`、`next_boundary_checked`、`output_pages`和`evidence`。disposition为`retained`或`user_removed`；后者另附`removal_instruction`且output_pages为空。原稿确缺/转换遗漏等未解项不能伪填retained。
- delivery的`visual`：`normal_reading_size:true`、`reviewed_pages`覆盖全部物理页、`evidence`为实看或合规继承记录；集合覆盖不能证明实际看过。

## 补充排版证据放在哪里

沿用既有证据文件：geometry记录版心/字体/段落/图片等测量与边界；reference_fidelity记录同尺度范本对照及残差；preview_fidelity记录真实媒体与比例；samples记录完整目录分页和高风险页型；visual记录每页观察/继承依据及相邻边界；reopen记录正式路径读回。

检查器不直接解析DOCX/PDF、不测字体、不识别遮挡、不证明来源清单无漏项，也不自动执行保存或视觉审查。成功只能称`receipt_consistent`，不能称“全册无错误”。
