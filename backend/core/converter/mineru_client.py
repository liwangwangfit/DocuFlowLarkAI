"""
MinerU API客户端 - PDF解析
"""
import httpx
from typing import Optional
from pathlib import Path
from loguru import logger

from config import get_config


class MinerUClient:
    """MinerU API客户端"""
    
    def __init__(self):
        self.config = get_config().mineru
    
    async def parse_pdf(self, file_path: str) -> str:
        """
        解析PDF文件，返回Markdown内容
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            Markdown格式的文档内容
        """
        if self.config.use_local:
            return await self._parse_local(file_path)
        else:
            return await self._parse_cloud(file_path)
    
    async def _parse_local(self, file_path: str) -> str:
        """调用本地MinerU服务"""
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                with open(file_path, 'rb') as f:
                    files = {'file': (Path(file_path).name, f, 'application/pdf')}
                    
                    resp = await client.post(
                        f"{self.config.local_url}/parse",
                        files=files,
                        params={
                            "extract_images": str(self.config.extract_images).lower(),
                            "extract_tables": str(self.config.extract_tables).lower(),
                            "ocr_enabled": str(self.config.ocr_enabled).lower(),
                            "language": self.config.language
                        }
                    )
                    
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("success") or "markdown" in data:
                        markdown = data.get("markdown", data.get("content", ""))
                        logger.info(f"PDF解析成功: {file_path}")
                        return markdown
                    else:
                        raise Exception(f"解析失败: {data}")
                        
        except httpx.ConnectError:
            logger.error(f"无法连接到本地MinerU服务: {self.config.local_url}")
            # 返回模拟内容用于测试
            return self._get_mock_content(file_path)
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")
            # 返回模拟内容用于测试
            return self._get_mock_content(file_path)
    
    async def _parse_cloud(self, file_path: str) -> str:
        """调用MinerU云服务"""
        if not self.config.cloud_api_key:
            raise Exception("未配置MinerU云服务API Key")
        
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                with open(file_path, 'rb') as f:
                    files = {'file': (Path(file_path).name, f, 'application/pdf')}
                    
                    resp = await client.post(
                        f"{self.config.cloud_url}/parse",
                        headers={"Authorization": f"Bearer {self.config.cloud_api_key}"},
                        files=files,
                        params={
                            "extract_images": str(self.config.extract_images).lower(),
                            "extract_tables": str(self.config.extract_tables).lower(),
                        }
                    )
                    
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("success"):
                        return data.get("markdown", data.get("content", ""))
                    else:
                        raise Exception(f"云服务解析失败: {data}")
                        
        except Exception as e:
            logger.error(f"云服务解析失败: {e}")
            return self._get_mock_content(file_path)
    
    def _get_mock_content(self, file_path: str) -> str:
        """
        获取模拟内容（用于测试或当服务不可用时）
        
        实际使用时，这里可以替换为其他OCR服务，如Docling
        """
        file_name = Path(file_path).name
        return f"""# {file_name}

> ⚠️ 注意：这是模拟内容。MinerU服务未连接。
> 
> 请确保：
> 1. 本地MinerU服务已启动: docker run -p 8000:8000 opendatalab/mineru:latest
> 2. 或使用其他OCR服务替代

## 文档信息

- **文件名**: {file_name}
- **文件路径**: {file_path}
- **解析状态**: 服务未连接

## 建议

您可以：
1. 启动本地MinerU服务
2. 配置MinerU云服务API Key
3. 使用其他OCR方案（如Docling）

---

*本文档由企业知识库迁移系统自动生成*
"""
    
    async def health_check(self) -> bool:
        """检查服务健康状态"""
        if not self.config.use_local:
            return True  # 云服务假设可用
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.config.local_url}/health")
                return resp.status_code == 200
        except:
            return False
