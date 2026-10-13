"""Impress CLI 命令"""

from __future__ import annotations

from pathlib import Path

import typer

from wps_cli.cli.common import handle_error, make_get_service, success
from wps_cli.consts import IMPRESS_INPUT_EXTENSIONS, PP_TRANSITION_RANDOM
from wps_cli.services.impress_service import ImpressService
from wps_cli.utils.path_utils import ensure_safe_input_path, ensure_safe_output_path

app = typer.Typer(help="PPT 演示文稿操作")

_get_service = make_get_service(ImpressService)


def _safe_impress_input(file: str):
    return ensure_safe_input_path(file, allowed_extensions=IMPRESS_INPUT_EXTENSIONS)


def _open_pres(svc: ImpressService, path: Path, readonly: bool = False):
    session = svc.manager.start("impress")
    try:
        session.app.Presentations.Open(str(path), ReadOnly=readonly)
        return session
    except Exception:
        svc.manager.stop(session.session_id)
        raise


@app.command()
def new(
    output: str = typer.Option("", "--output", "-o", help="输出路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """新建空白演示文稿"""
    cmd = "impress.new"
    try:
        out_path = ensure_safe_output_path(output) if output else None
        result = _get_service().new(out_path)
        success({"path": str(result)}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def info(
    file: str = typer.Argument(..., help="文件路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """输出演示文稿元信息"""
    cmd = "impress.info"
    try:
        path = _safe_impress_input(file)
        result = _get_service().info(path)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_list(
    file: str = typer.Argument(..., help="文件路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """列出所有幻灯片"""
    cmd = "impress.slide_list"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            result = svc.slide_list(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output, headers=["index", "title", "layout"])
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_add(
    file: str = typer.Argument(..., help="文件路径"),
    layout: int = typer.Option(1, "--layout", "-l", help="版式编号"),
    at: int = typer.Option(0, "--at", "-a", help="插入位置"),
    title: str = typer.Option("", "--title", "-t", help="标题文本"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """新增幻灯片"""
    cmd = "impress.slide_add"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            idx = svc.slide_add(session.app, layout, at if at else None, title)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"index": idx}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_delete(
    file: str = typer.Argument(..., help="文件路径"),
    index: int = typer.Argument(..., help="幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """删除幻灯片"""
    cmd = "impress.slide_delete"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.slide_delete(session.app, index)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"deleted": index}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_duplicate(
    file: str = typer.Argument(..., help="文件路径"),
    index: int = typer.Argument(..., help="幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """复制指定幻灯片并保存"""
    cmd = "impress.slide_duplicate"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            new_index = svc.slide_duplicate(session.app, index)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"source": index, "index": new_index}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_move(
    file: str = typer.Argument(..., help="文件路径"),
    from_index: int = typer.Option(..., "--from", help="原幻灯片编号"),
    to_index: int = typer.Option(..., "--to", help="目标幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """移动幻灯片并保存"""
    cmd = "impress.slide_move"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.slide_move(session.app, from_index, to_index)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"from": from_index, "to": to_index}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command("slides-insert")
def slides_insert(
    file: str = typer.Argument(..., help="目标演示文稿路径"),
    source: str = typer.Option(..., "--source", help="来源演示文稿路径"),
    after: int = typer.Option(-1, "--after", help="插入到第几页之后；默认末尾"),
    start: int = typer.Option(0, "--start", help="来源起始页；默认全部"),
    end: int = typer.Option(0, "--end", help="来源结束页；默认至末尾"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """从另一个PPT整页导入，保留来源格式"""
    cmd = "impress.slides_insert"
    try:
        path = _safe_impress_input(file)
        source_path = _safe_impress_input(source)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            result = svc.slides_insert_from_file(
                session.app,
                source_path,
                None if after < 0 else after,
                start if start > 0 else None,
                end if end > 0 else None,
            )
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({**result, "source": str(source_path)}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def text_set(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    placeholder: str = typer.Option(
        "title", "--placeholder", "-p", help="占位符: title/body/subtitle"
    ),
    text: str = typer.Option(..., "--text", "-t", help="文本内容"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """设置幻灯片文本"""
    cmd = "impress.text_set"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.text_set(session.app, slide, placeholder, text)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide, "placeholder": placeholder}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def text_get(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """提取幻灯片文本"""
    cmd = "impress.text_get"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            result = svc.text_get(session.app, slide)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide, "text": result}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def shape_list(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """列出指定幻灯片的形状及其精确几何信息"""
    cmd = "impress.shape_list"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            result = svc.shape_list(session.app, slide)
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def shape_text_set(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    shape: int = typer.Option(..., "--shape", help="形状编号"),
    text: str = typer.Option(..., "--text", "-t", help="文本内容"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """按形状编号精确修改文字"""
    cmd = "impress.shape_text_set"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            result = svc.shape_text_set(session.app, slide, shape, text)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def shape_position_set(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    shape: int = typer.Option(..., "--shape", help="形状编号"),
    left: float | None = typer.Option(None, "--left", help="左坐标"),
    top: float | None = typer.Option(None, "--top", help="上坐标"),
    width: float | None = typer.Option(None, "--width", help="宽度"),
    height: float | None = typer.Option(None, "--height", help="高度"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """按形状编号设置位置和尺寸"""
    cmd = "impress.shape_position_set"
    try:
        if all(value is None for value in (left, top, width, height)):
            raise ValueError("至少提供 left/top/width/height 中的一项")
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            result = svc.shape_position_set(
                session.app,
                slide,
                shape,
                left=left,
                top=top,
                width=width,
                height=height,
            )
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def image_insert(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    image: str = typer.Option(..., "--image", "-i", help="图片路径"),
    left: float = typer.Option(100, "--left", help="左边距"),
    top: float = typer.Option(100, "--top", help="上边距"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """插入图片"""
    cmd = "impress.image_insert"
    try:
        path = _safe_impress_input(file)
        image_path = ensure_safe_input_path(image)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.image_insert(session.app, slide, image_path, left, top)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide, "image": str(image_path)}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def image_replace(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    shape: int = typer.Option(..., "--shape", help="原图片形状编号"),
    image: str = typer.Option(..., "--image", "-i", help="新图片路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """原位替换图片并保留位置、尺寸和旋转"""
    cmd = "impress.image_replace"
    try:
        path = _safe_impress_input(file)
        image_path = ensure_safe_input_path(image)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            result = svc.image_replace(session.app, slide, shape, image_path)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({**result, "image": str(image_path)}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def notes_set(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    text: str = typer.Option(..., "--text", "-t", help="备注文本"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """设置幻灯片演讲者备注"""
    cmd = "impress.notes_set"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.notes_set(session.app, slide, text)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def notes_get(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """读取幻灯片演讲者备注"""
    cmd = "impress.notes_get"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            result = svc.notes_get(session.app, slide)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide, "text": result}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def transition_set(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    effect: int = typer.Option(PP_TRANSITION_RANDOM, "--effect", help="WPS切换效果常量"),
    duration: float = typer.Option(1.0, "--duration", help="切换持续时间"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """设置幻灯片切换效果"""
    cmd = "impress.transition_set"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            svc.transition_set(session.app, slide, effect, duration)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success({"slide": slide, "effect": effect, "duration": duration}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def slide_export_image(
    file: str = typer.Argument(..., help="文件路径"),
    slide: int = typer.Option(..., "--slide", "-s", help="幻灯片编号"),
    output: str = typer.Option(..., "--output", "-o", help="PNG/JPG/GIF/BMP输出路径"),
    width: int = typer.Option(1920, "--width", help="输出宽度"),
    height: int = typer.Option(1080, "--height", help="输出高度"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """将指定幻灯片导出成图片并检查实际文件"""
    cmd = "impress.slide_export_image"
    try:
        path = _safe_impress_input(file)
        out_path = ensure_safe_output_path(output)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            result = svc.slide_export_image(session.app, slide, out_path, width, height)
        finally:
            svc.manager.stop(session.session_id)
        success(
            {"slide": slide, "path": str(result), "bytes": result.stat().st_size},
            command=cmd,
            json_mode=json_output,
        )
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def export_pdf(
    file: str = typer.Argument(..., help="文件路径"),
    output: str = typer.Option("", "--output", "-o", help="输出路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """导出为 PDF"""
    cmd = "impress.export_pdf"
    try:
        path = _safe_impress_input(file)
        out_path = ensure_safe_output_path(output) if output else path.with_suffix(".pdf")
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            svc.export_pdf(session.app, out_path)
        finally:
            svc.manager.stop(session.session_id)
        success({"path": str(out_path)}, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


# ── Validate 验证命令 ──
# 设计参考: iOfficeAI/OfficeCLI (Apache 2.0)


@app.command()
def validate(
    file: str = typer.Argument(..., help="文件路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """验证 PPT 演示文稿完整性

    设计参考: iOfficeAI/OfficeCLI (Apache 2.0)

    检查项: 超链接有效性、嵌入媒体完整性、幻灯片大小一致性、母版引用
    """
    cmd = "impress.validate"
    try:
        path = _safe_impress_input(file)
        from wps_cli.services.validate_service import ValidateService

        svc = ValidateService(manager=_get_service().manager)
        result = svc.validate_impress(path)
        success(
            {
                "passed": result.passed,
                "file": result.file,
                "checks": result.checks,
                "issues_count": result.issues_count,
                "errors_count": result.errors_count,
                "warnings_count": result.warnings_count,
            },
            command=cmd,
            json_mode=json_output,
        )
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


# ── Refresh 刷新命令 ──
# 设计参考: iOfficeAI/OfficeCLI (Apache 2.0)


@app.command()
def refresh(
    file: str = typer.Argument(..., help="文件路径"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """刷新演示文稿链接

    设计参考: iOfficeAI/OfficeCLI (Apache 2.0)

    更新所有 OLE 链接、图表数据和嵌入对象。
    """
    cmd = "impress.refresh"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path)
        try:
            result = svc.refresh(session.app)
            svc.save(session.app)
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


# ── 语义视图与路径定位（Phase 4）──
# 设计参考: iOfficeAI/OfficeCLI (Apache 2.0)


@app.command("view")
def view(
    file: str = typer.Argument(..., help="文件路径"),
    view_type: str = typer.Argument("summary", help="视图类型: summary/issues/slides/annotated/stats"),
    type_filter: str = typer.Option("", "--type", "-t", help="过滤问题子类型（仅对 issues 视图有效）"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """演示文稿语义视图（参考 OfficeCLI L1 Read）

    设计参考: iOfficeAI/OfficeCLI (Apache 2.0)

    支持五种视图:
      summary   — 演示文稿结构摘要（幻灯片/切换/备注）
      issues    — 文档诊断（文本溢出/字体/图片/切换时间），可用 --type 过滤子类型
      slides    — 幻灯片列表概览
      annotated — 带路径标注的形状内容
      stats     — 纯数字统计
    """
    cmd = f"impress.view_{view_type}"
    try:
        path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, path, readonly=True)
        try:
            if view_type == "summary":
                result = svc.summarize(session.app)
            elif view_type == "issues":
                result = svc.diagnose(session.app)
                if type_filter:
                    result = [r for r in result if r.get("subtype", "") == type_filter]
            elif view_type == "slides":
                result = svc.slide_list(session.app)
            elif view_type == "annotated":
                result = svc.annotate(session.app)
            elif view_type == "stats":
                result = svc.get_stats(session.app)
            else:
                from wps_cli.exceptions import ValidationError

                raise ValidationError(
                    f"不支持的视图类型: {view_type}",
                    suggestion="可选: summary, issues, slides, annotated, stats",
                )
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)


@app.command()
def get(
    file: str = typer.Argument(..., help="文件路径"),
    path: str = typer.Argument(..., help="元素路径，如 /slide[1]/shape[2]"),
    json_output: bool = typer.Option(False, "--json", "-j", help="JSON 输出"),
):
    """通过路径获取演示文稿元素内容

    设计参考: iOfficeAI/OfficeCLI (Apache 2.0)

    Examples:
        wps impress get pres.pptx "/slide[1]/shape[2]"
        wps impress get pres.pptx "/slide[1]/shape[2]/text[1]"
        wps impress get pres.pptx "/slide[3]/notes"
    """
    cmd = "impress.get"
    try:
        file_path = _safe_impress_input(file)
        svc = _get_service()
        session = _open_pres(svc, file_path, readonly=True)
        try:
            from wps_cli.services.path_resolver import PathResolver

            resolver = PathResolver()
            obj = resolver.resolve(session.app, "impress", path)
            content = str(obj.Text if hasattr(obj, "Text") else obj)
            result = {"path": path, "content": content}
        finally:
            svc.manager.stop(session.session_id)
        success(result, command=cmd, json_mode=json_output)
    except Exception as e:
        handle_error(e, command=cmd, json_mode=json_output)
