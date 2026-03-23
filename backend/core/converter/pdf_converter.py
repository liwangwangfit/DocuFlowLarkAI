"""
PDF转换器
"""
import re
from pathlib import Path
from typing import Optional
from loguru import logger

from .base import BaseConverter, ConversionResult, DocumentType
from .mineru_client import MinerUClient


class PDFConverter(BaseConverter):
    """PDF转换器"""
    
    def __init__(self):
        self.mineru = MinerUClient()
    
    def supports(self, doc_type: DocumentType) -> bool:
        return doc_type == DocumentType.PDF
    
    async def convert(self, file_path: str) -> ConversionResult:
        """
        PDF转换流程:
        1. 调用MinerU解析PDF → Markdown
        2. 提取元数据
        """
        try:
            # 调用MinerU获取Markdown
            markdown_content = await self.mineru.parse_pdf(file_path)
            
            # 提取元数据
            metadata = {
                'source_type': 'pdf',
                'page_count': self._extract_page_count(markdown_content),
                'has_images': '![image]' in markdown_content or '![图片]' in markdown_content,
                'has_tables': '|' in markdown_content,
                'title': self._extract_title(markdown_content, file_path)
            }
            
            # 清理和优化Markdown
            cleaned_content = self._clean_markdown(markdown_content)
            
            return ConversionResult(
                success=True,
                content=cleaned_content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"PDF转换失败: {e}")
            return ConversionResult(
                success=False,
                error_message=str(e),
                metadata={'source_type': 'pdf', 'file_path': file_path}
            )
    
    def _extract_page_count(self, markdown: str) -> int:
        """从Markdown提取页数信息"""
        # MinerU返回的Markdown可能包含页码标记
        pages = re.findall(r'<!--\s*[Pp]age\s*(\d+)\s*-->', markdown)
        if pages:
            return len(set(pages))
        
        # 估算：通常每页300-500字符
        char_count = len(markdown)
        estimated_pages = max(1, char_count // 400)
        return min(estimated_pages, 1000)  # 上限1000页
    
    def _extract_title(self, markdown: str, file_path: str) -> str:
        """提取文档标题"""
        # 尝试从第一行提取
        lines = markdown.strip().split('\n')
        for line in lines[:10]:
            line = line.strip()
            # 查找Markdown标题
            if line.startswith('# '):
                return line[2:].strip()
        
        # 使用文件名
        return Path(file_path).stem
    
    def _clean_markdown(self, markdown: str) -> str:
        """清理Markdown内容"""
        # 移除多余的空行
        content = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # 标准化图片引用（MinerU可能使用不同格式）
        content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'![\1](\2)', content)
        
        # 移除可能的特殊标记
        content = re.sub(r'<!--\s*[Pp]age\s*\d+\s*-->', '', content)
        
        return content.strip()
