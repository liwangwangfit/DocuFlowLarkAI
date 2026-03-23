"""
转换器工厂
"""
from pathlib import Path
from typing import Optional, List
from loguru import logger

from .base import BaseConverter, DocumentType
from .pdf_converter import PDFConverter
from .excel_converter import ExcelConverter
from .doc_converter import DocConverter


class ConverterFactory:
    """转换器工厂"""
    
    _converters: List[BaseConverter] = []
    _initialized = False
    
    @classmethod
    def _ensure_initialized(cls):
        """确保已初始化"""
        if not cls._initialized:
            cls.register(PDFConverter())
            cls.register(ExcelConverter())
            cls.register(DocConverter())
            cls._initialized = True
    
    @classmethod
    def register(cls, converter: BaseConverter):
        """注册转换器"""
        cls._converters.append(converter)
        logger.debug(f"注册转换器: {converter.__class__.__name__}")
    
    @classmethod
    def get_converter(cls, file_path: str) -> Optional[BaseConverter]:
        """根据文件路径获取合适的转换器"""
        cls._ensure_initialized()
        
        doc_type = cls._detect_type(file_path)
        for converter in cls._converters:
            if converter.supports(doc_type):
                return converter
        
        logger.warning(f"未找到支持 {doc_type} 的转换器")
        return None
    
    @classmethod
    def _detect_type(cls, file_path: str) -> DocumentType:
        """检测文档类型"""
        ext = Path(file_path).suffix.lower()
        
        type_map = {
            '.pdf': DocumentType.PDF,
            '.doc': DocumentType.DOC,
            '.docx': DocumentType.DOCX,
            '.xls': DocumentType.XLS,
            '.xlsx': DocumentType.XLSX,
            '.txt': DocumentType.TXT,
            '.md': DocumentType.MD,
            '.html': DocumentType.HTML,
            '.htm': DocumentType.HTML,
            '.ppt': DocumentType.PPT,
            '.pptx': DocumentType.PPTX,
        }
        
        return type_map.get(ext, DocumentType.TXT)
    
    @classmethod
    def list_supported_types(cls) -> List[str]:
        """列出支持的文件类型"""
        return ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.md']
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """检查文件是否受支持"""
        return cls.get_converter(file_path) is not None
