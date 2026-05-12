"""
文档转换器基类
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel


class DocumentType(Enum):
    """文档类型"""
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"
    HTML = "html"
    PPT = "ppt"
    PPTX = "pptx"
    XMIND = "xmind"
    FREEMIND = "mm"
    OPML = "opml"


class ConversionResult(BaseModel):
    """转换结果"""
    success: bool
    output_path: Optional[str] = None
    content: Optional[str] = None  # Markdown或JSON内容
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseConverter(ABC):
    """文档转换器基类"""
    
    @abstractmethod
    async def convert(self, file_path: str) -> ConversionResult:
        """执行转换"""
        pass
    
    @abstractmethod
    def supports(self, doc_type: DocumentType) -> bool:
        """是否支持该文档类型"""
        pass
