"""
思维导图转换器 - 将 XMind / FreeMind (.mm) / OPML 转换为 Markdown
"""
import json
import tempfile
import zipfile
from pathlib import Path
from typing import List
from xml.etree import ElementTree as ET

from loguru import logger

from .base import BaseConverter, ConversionResult, DocumentType


class MindMapConverter(BaseConverter):
    """将 XMind (.xmind)、FreeMind (.mm)、OPML (.opml) 转换为 Markdown"""

    SUPPORTED_EXTENSIONS = {".xmind", ".mm", ".opml"}

    def supports(self, doc_type: DocumentType) -> bool:
        return False  # uses extension-based dispatch instead

    def supports_extension(self, ext: str) -> bool:
        return ext.lower() in self.SUPPORTED_EXTENSIONS

    async def convert(self, file_path: str) -> ConversionResult:
        ext = Path(file_path).suffix.lower()
        try:
            if ext == ".xmind":
                return await self._convert_xmind(file_path)
            elif ext == ".mm":
                return await self._convert_freemind(file_path)
            elif ext == ".opml":
                return await self._convert_opml(file_path)
            else:
                return ConversionResult(
                    success=False,
                    error_message=f"MindMapConverter 不支持扩展名: {ext}"
                )
        except Exception as e:
            logger.error(f"思维导图转换失败 ({ext}): {e}")
            return ConversionResult(success=False, error_message=str(e))

    # ── XMind ────────────────────────────────────────────────────────

    async def _convert_xmind(self, file_path: str) -> ConversionResult:
        """XMind 文件是 ZIP 包，内含 content.json 或 content.xml"""
        source = Path(file_path)
        with zipfile.ZipFile(file_path, "r") as zf:
            names = zf.namelist()

            if "content.json" in names:
                raw = zf.read("content.json").decode("utf-8")
                data = json.loads(raw)
                lines = self._xmind_json_to_md(data)
            elif "content.xml" in names:
                raw = zf.read("content.xml").decode("utf-8")
                lines = self._xmind_xml_to_md(raw)
            else:
                return ConversionResult(
                    success=False,
                    error_message="XMind 文件中未找到 content.json 或 content.xml"
                )

        md_text = "\n".join(lines)
        output_path = self._write_md(source.stem, md_text)
        return ConversionResult(
            success=True,
            output_path=output_path,
            content=md_text,
            metadata={"source_type": "xmind", "title": source.stem},
        )

    def _xmind_json_to_md(self, data) -> List[str]:
        """解析 XMind 8+ JSON 格式"""
        lines: List[str] = []
        sheets = data if isinstance(data, list) else [data]
        for sheet in sheets:
            root_topic = sheet.get("rootTopic") or sheet.get("topic", {})
            title = root_topic.get("title", "未命名")
            lines.append(f"# {title}")
            lines.append("")
            self._walk_xmind_topic(root_topic.get("children", {}).get("attached", []),
                                   lines, depth=2)
        return lines

    def _walk_xmind_topic(self, topics: list, lines: List[str], depth: int):
        for topic in topics:
            title = topic.get("title", "")
            if depth <= 6:
                lines.append(f"{'#' * depth} {title}")
            else:
                indent = "  " * (depth - 6)
                lines.append(f"{indent}- {title}")
            lines.append("")
            children = topic.get("children", {}).get("attached", [])
            if children:
                self._walk_xmind_topic(children, lines, depth + 1)

    def _xmind_xml_to_md(self, xml_text: str) -> List[str]:
        """解析旧版 XMind XML 格式"""
        lines: List[str] = []
        root = ET.fromstring(xml_text)
        ns = {"xmind": "urn:xmind:xmap:xmlns:content:2.0"}

        for sheet in root.findall(".//xmind:sheet", ns):
            topic = sheet.find("xmind:topic", ns)
            if topic is not None:
                self._walk_xmind_xml_topic(topic, lines, 1, ns)
        if not lines:
            for topic in root.iter():
                if topic.tag.endswith("topic"):
                    self._walk_xmind_xml_topic(topic, lines, 1, {})
                    break
        return lines

    def _walk_xmind_xml_topic(self, elem, lines: List[str], depth: int, ns: dict):
        title_el = elem.find("xmind:title", ns) if ns else elem.find("title")
        if title_el is None:
            for child in elem:
                if child.tag.endswith("title"):
                    title_el = child
                    break
        title = (title_el.text or "").strip() if title_el is not None else ""
        if title:
            if depth <= 6:
                lines.append(f"{'#' * depth} {title}")
            else:
                lines.append(f"{'  ' * (depth - 6)}- {title}")
            lines.append("")

        children_el = elem.find("xmind:children", ns) if ns else None
        if children_el is None:
            for child in elem:
                if child.tag.endswith("children"):
                    children_el = child
                    break

        if children_el is not None:
            topics_el = children_el.find("xmind:topics", ns) if ns else None
            if topics_el is None:
                for child in children_el:
                    if child.tag.endswith("topics"):
                        topics_el = child
                        break
            container = topics_el if topics_el is not None else children_el
            for child_topic in container:
                if child_topic.tag.endswith("topic"):
                    self._walk_xmind_xml_topic(child_topic, lines, depth + 1, ns)

    # ── FreeMind (.mm) ───────────────────────────────────────────────

    async def _convert_freemind(self, file_path: str) -> ConversionResult:
        source = Path(file_path)
        tree = ET.parse(file_path)
        root = tree.getroot()
        lines: List[str] = []
        for node in root.findall("node"):
            self._walk_freemind_node(node, lines, 1)
        md_text = "\n".join(lines)
        output_path = self._write_md(source.stem, md_text)
        return ConversionResult(
            success=True,
            output_path=output_path,
            content=md_text,
            metadata={"source_type": "mm", "title": source.stem},
        )

    def _walk_freemind_node(self, node, lines: List[str], depth: int):
        text = node.get("TEXT", "") or node.get("text", "")
        if text:
            if depth <= 6:
                lines.append(f"{'#' * depth} {text}")
            else:
                lines.append(f"{'  ' * (depth - 6)}- {text}")
            lines.append("")
        for child in node.findall("node"):
            self._walk_freemind_node(child, lines, depth + 1)

    # ── OPML ────────────────────────────────────────────────────────

    async def _convert_opml(self, file_path: str) -> ConversionResult:
        source = Path(file_path)
        tree = ET.parse(file_path)
        root = tree.getroot()

        title = ""
        head = root.find("head")
        if head is not None:
            title_el = head.find("title")
            if title_el is not None and title_el.text:
                title = title_el.text.strip()
        if not title:
            title = source.stem

        lines = [f"# {title}", ""]
        body = root.find("body")
        if body is not None:
            for outline in body.findall("outline"):
                self._walk_opml_outline(outline, lines, 2)

        md_text = "\n".join(lines)
        output_path = self._write_md(source.stem, md_text)
        return ConversionResult(
            success=True,
            output_path=output_path,
            content=md_text,
            metadata={"source_type": "opml", "title": title},
        )

    def _walk_opml_outline(self, outline, lines: List[str], depth: int):
        text = outline.get("text", "") or outline.get("title", "")
        if text:
            if depth <= 6:
                lines.append(f"{'#' * depth} {text}")
            else:
                lines.append(f"{'  ' * (depth - 6)}- {text}")
            lines.append("")
        for child in outline.findall("outline"):
            self._walk_opml_outline(child, lines, depth + 1)

    # ── Utility ──────────────────────────────────────────────────────

    @staticmethod
    def _write_md(stem: str, content: str) -> str:
        output_dir = tempfile.mkdtemp(prefix="docuflow_mm_")
        output_path = Path(output_dir) / f"{stem}.md"
        output_path.write_text(content, encoding="utf-8")
        return str(output_path)
