"""
飞书云空间/Drive API 封装 - 文件导入相关接口
使用 user_access_token
"""
import httpx
import asyncio
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
from loguru import logger

from .auth import feishu_oauth


class FeishuDriveAPI:
    """飞书云空间API封装 - 导入文件功能"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    # 文件类型映射：扩展名 -> (飞书目标类型, 上传时的 file_extension)
    FILE_TYPE_MAP = {
        # 文档类型 -> 导入为 docx
        "docx": ("docx", "docx"),
        "doc": ("docx", "doc"),
        "txt": ("docx", "txt"),
        "md": ("docx", "md"),
        "mark": ("docx", "mark"),
        "markdown": ("docx", "markdown"),
        "html": ("docx", "html"),
        # 表格类型 -> 导入为 sheet
        "xlsx": ("sheet", "xlsx"),
        "csv": ("sheet", "csv"),
        "xls": ("sheet", "xls"),
        # PPT -> 导入为 docx（飞书知识库原生支持）
        "pptx": ("docx", "pptx"),
        # 思维导图 -> 导入为 docx（飞书知识库原生支持）
        "xmind": ("docx", "xmind"),
        "mm": ("docx", "mm"),
        "opml": ("docx", "opml"),
    }
    
    async def _get_headers(self, content_type: str = "application/json") -> Dict[str, str]:
        """获取请求头"""
        token = await feishu_oauth.get_user_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = f"{content_type}; charset=utf-8"
        return headers
    
    def _get_file_type_info(self, file_path: str) -> Tuple[str, str]:
        """
        根据文件扩展名获取导入类型信息
        
        Returns:
            (obj_type, file_extension): 对象类型和文件扩展名
        """
        ext = Path(file_path).suffix.lower().lstrip(".")
        
        if ext not in self.FILE_TYPE_MAP:
            raise ValueError(f"不支持的文件类型: {ext}，支持的类型: {list(self.FILE_TYPE_MAP.keys())}")
        
        return self.FILE_TYPE_MAP[ext]
    
    async def upload_media(self, file_path: str) -> str:
        """
        上传素材文件（用于导入）
        
        API: POST /open-apis/drive/v1/medias/upload_all
        权限: drive:media:upload
        
        Args:
            file_path: 本地文件路径
            
        Returns:
            file_token: 文件token，用于后续导入
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 获取文件类型信息
        obj_type, file_extension = self._get_file_type_info(file_path)
        
        # 构建 extra 参数
        extra = f'{{"obj_type":"{obj_type}","file_extension":"{file_extension}"}}'
        
        # 获取文件大小
        file_size = path.stat().st_size
        
        logger.info(f"上传素材: {path.name}, 大小: {file_size} bytes, 导入类型: {obj_type}")
        
        # 获取 token（multipart请求不需要Content-Type，httpx会自动设置）
        token = await feishu_oauth.get_user_access_token()
        
        async with httpx.AsyncClient(timeout=300) as client:
            # 先读取文件内容
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            # 构建 multipart 表单数据
            # parent_node 是必填参数，ccm_import_open 类型可为空字符串
            files = {
                "file": (path.name, file_content, "application/octet-stream"),
                "file_name": (None, path.name),
                "parent_type": (None, "ccm_import_open"),
                "parent_node": (None, ""),
                "size": (None, str(file_size)),
                "extra": (None, extra),
            }
            
            resp = await client.post(
                f"{self.BASE_URL}/drive/v1/medias/upload_all",
                headers={"Authorization": f"Bearer {token}"},
                files=files
            )
            
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") == 0:
                file_token = result["data"]["file_token"]
                logger.info(f"素材上传成功: {file_token}")
                return file_token
            else:
                raise Exception(f"素材上传失败: {result}")
    
    async def create_import_task(self, file_token: str, file_extension: str, 
                                  import_type: str, file_name: str = "") -> str:
        """
        创建导入任务
        
        API: POST /open-apis/drive/v1/import_tasks
        权限: drive:import_task:create
        
        Args:
            file_token: 上传素材返回的 file_token
            file_extension: 文件扩展名（如 docx, xlsx）
            import_type: 导入类型（docx/sheet/bitable）
            file_name: 导入后的文件名（可选，默认为原文件名）
            
        Returns:
            ticket: 导入任务ID，用于查询导入结果
        """
        headers = await self._get_headers()
        
        json_data = {
            "file_token": file_token,
            "file_extension": file_extension,
            "type": import_type,
            "point": {
                "mount_type": 1,  # 挂载到云空间
                "mount_key": ""   # 空字符串表示根目录
            }
        }
        
        if file_name:
            json_data["file_name"] = file_name
        
        logger.info(f"创建导入任务: file_token={file_token}, type={import_type}, ext={file_extension}")
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/drive/v1/import_tasks",
                headers=headers,
                json=json_data
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") == 0:
                ticket = result["data"]["ticket"]
                logger.info(f"导入任务创建成功: ticket={ticket}")
                return ticket
            else:
                raise Exception(f"创建导入任务失败: {result}")
    
    async def get_import_task_result(self, ticket: str) -> Dict[str, Any]:
        """
        查询导入任务结果
        
        API: GET /open-apis/drive/v1/import_tasks/{ticket}
        权限: docs:document:import
        
        Args:
            ticket: 导入任务ID
            
        Returns:
            导入任务结果，包含 job_status, token, url 等
            job_status: 0=成功, 1=初始化, 2=处理中, 其他=错误
        """
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/drive/v1/import_tasks/{ticket}",
                headers=headers
            )
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") == 0:
                # 响应结构: data.result 包含具体结果
                return result["data"]["result"]
            else:
                raise Exception(f"查询导入任务失败: {result}")
    
    async def import_file(self, file_path: str, max_retries: int = 60, retry_interval: int = 2) -> Dict[str, Any]:
        """
        完整的文件导入流程（上传 + 导入 + 轮询结果）
        
        Args:
            file_path: 本地文件路径
            max_retries: 最大轮询次数，默认60次（2分钟）
            retry_interval: 轮询间隔秒数
            
        Returns:
            导入结果，包含:
            - token: 文档token
            - type: 文档类型（docx/sheet/bitable）
            - title: 文档标题
            - url: 文档URL
        """
        path = Path(file_path)
        original_title = path.stem
        
        # 获取文件类型信息
        obj_type, file_extension = self._get_file_type_info(file_path)
        
        # 步骤1: 上传素材
        file_token = await self.upload_media(file_path)
        
        # 步骤2: 创建导入任务
        ticket = await self.create_import_task(
            file_token=file_token,
            file_extension=file_extension,
            import_type=obj_type,
            file_name=original_title
        )
        
        # 步骤3: 轮询导入结果
        logger.info(f"开始轮询导入结果: ticket={ticket}")
        
        for i in range(max_retries):
            result = await self.get_import_task_result(ticket)
            job_status = result.get("job_status")
            doc_type = result.get("type", obj_type)
            
            logger.debug(f"导入任务状态: {job_status} (第{i+1}次查询)")
            
            # job_status: 0=成功, 1=初始化, 2=处理中, 其他=错误
            if job_status == 0:
                # 导入成功，提取文档信息
                logger.info(f"导入成功，完整结果: {result}")
                
                doc_token = result.get("token")
                doc_url = result.get("url")
                doc_title = result.get("file_name") or original_title
                
                # 兼容处理：检查其他可能的字段名
                if not doc_token:
                    if doc_type == "docx":
                        doc_token = result.get("docx_token")
                    elif doc_type == "sheet":
                        doc_token = result.get("sheet_token")
                    elif doc_type == "bitable":
                        doc_token = result.get("bitable_token")
                
                if not doc_token:
                    raise Exception(f"导入成功但未找到文档token，结果: {result}")
                
                return {
                    "token": doc_token,
                    "type": doc_type,
                    "title": doc_title,
                    "url": doc_url or "",
                }
            
            elif job_status == 1 or job_status == 2:
                # 仍在处理中，等待后重试
                await asyncio.sleep(retry_interval)
                continue
            
            elif job_status is not None and job_status > 2:
                # 错误状态
                error_msg = result.get("job_error_msg", f"导入失败(错误码:{job_status})")
                raise Exception(f"导入失败: {error_msg}")
            
            else:
                raise Exception(f"未知的导入状态: {job_status}")
        
        raise TimeoutError(f"导入任务超时，ticket={ticket}")


# 全局实例
drive_api = FeishuDriveAPI()
