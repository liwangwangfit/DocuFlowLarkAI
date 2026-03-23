"""
飞书文档API封装 - 使用 user_access_token
"""
import httpx
import re
import uuid
from typing import List, Dict, Optional, Any, Tuple
from loguru import logger

from .auth import feishu_oauth


class FeishuDocumentAPI:
    """飞书文档API封装"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    async def _get_headers(self) -> Dict[str, str]:
        """获取请求头（包含 user_access_token）"""
        token = await feishu_oauth.get_user_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
    
    async def create_document(self, title: str, folder_token: Optional[str] = None) -> str:
        """
        创建文档
        
        API: POST /open-apis/docx/v1/documents
        权限: docx:document:create
        
        Args:
            title: 文档标题
            folder_token: 文件夹token(可选)
            
        Returns:
            document_id: 文档ID
        """
        headers = await self._get_headers()
        
        json_data = {"title": title}
        if folder_token:
            json_data["folder_token"] = folder_token
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/docx/v1/documents",
                headers=headers,
                json=json_data
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 0:
                doc_id = data["data"]["document"]["document_id"]
                logger.info(f"文档创建成功: {doc_id}")
                return doc_id
            else:
                raise Exception(f"创建文档失败: {data}")
    
    async def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        获取文档信息
        
        API: GET /open-apis/docx/v1/documents/{document_id}
        """
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/docx/v1/documents/{document_id}",
                headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 0:
                return data["data"]["document"]
            else:
                raise Exception(f"获取文档失败: {data}")
    
    async def convert_markdown_to_blocks(self, markdown: str) -> List[Dict]:
        """
        Markdown转换为飞书Blocks
        
        API: POST /open-apis/docx/v1/documents/blocks/convert
        权限: docx:document.block:convert
        
        注意事项:
        1. 返回的Table块需要去除merge_info字段
        2. Image块需要先插入占位符，再上传图片替换
        
        Args:
            markdown: Markdown格式内容
            
        Returns:
            blocks列表
        """
        headers = await self._get_headers()
        
        # 清理Markdown内容，移除可能导致问题的字符
        markdown = self._sanitize_markdown(markdown)
        
        logger.info(f"开始转换Markdown，长度: {len(markdown)} chars，预览: {markdown[:100]}...")
        
        # 飞书API有长度限制，需要分段处理
        max_length = 50000
        
        if len(markdown) > max_length:
            logger.warning(f"Markdown内容过长 ({len(markdown)} chars)，将分段转换")
            all_blocks = []
            chunks = self._split_markdown(markdown, max_length)
            for chunk in chunks:
                blocks = await self._convert_single(chunk, headers)
                all_blocks.extend(blocks)
            return all_blocks
        else:
            return await self._convert_single(markdown, headers)
    
    def _sanitize_markdown(self, markdown: str) -> str:
        """清理Markdown内容，移除可能导致问题的字符"""
        # 移除 null 字符
        markdown = markdown.replace('\x00', '')
        # 移除控制字符（保留换行、制表符）
        import re
        markdown = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', markdown)
        # 确保内容不为空
        if not markdown.strip():
            markdown = "# 无内容\n\n该文档内容为空。"
        return markdown
    
    async def _convert_single(self, markdown: str, headers: Dict[str, str]) -> List[Dict]:
        """单次转换"""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE_URL}/docx/v1/documents/blocks/convert",
                headers=headers,
                json={
                    "content_type": "markdown",
                    "content": markdown
                }
            )
            # 先读取响应内容用于调试
            try:
                data = resp.json()
            except:
                data = {"text": resp.text}
            
            logger.info(f"blocks/convert 响应: status={resp.status_code}, code={data.get('code')}")
            
            if resp.status_code != 200 or data.get("code") != 0:
                logger.error(f"转换失败: {data}")
                error_msg = data.get('msg', '') or data.get('error', '') or str(data)
                raise Exception(f"Markdown转换失败: {error_msg}")
            
            blocks = data["data"]["blocks"]
            logger.info(f"blocks/convert 返回 {len(blocks)} 个块")
            if blocks:
                logger.debug(f"第一个块类型: {blocks[0].get('block_type')}, 键: {list(blocks[0].keys())}")
            
            # 处理Table块: 去除merge_info，并添加block_id
            blocks = self._sanitize_table_blocks(blocks)
            
            logger.info(f"转换后得到 {len(blocks)} 个块用于插入")
            
            return blocks
    
    def _split_markdown(self, markdown: str, max_length: int) -> List[str]:
        """将Markdown分割成多个块"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        lines = markdown.split('\n')
        for line in lines:
            if current_length + len(line) > max_length and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            
            current_chunk.append(line)
            current_length += len(line) + 1
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _sanitize_table_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """清理Table块的merge_info字段，并确保每个块有block_id"""
        import uuid
        for block in blocks:
            if not isinstance(block, dict):
                continue
                
            # 确保有block_id
            if not block.get('block_id'):
                block['block_id'] = str(uuid.uuid4())
            
            # 清理Table块的merge_info (在 property 中)
            block_type = block.get('block_type')
            if block_type == 31 or block_type == 'table':  # table block
                table_data = block.get('table', {})
                if isinstance(table_data, dict):
                    property_data = table_data.get('property', {})
                    if isinstance(property_data, dict) and 'merge_info' in property_data:
                        del table_data['property']['merge_info']
                        logger.debug(f"已删除 table.property.merge_info")
        return blocks
    
    def _prepare_blocks_for_descendant(self, blocks: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        将 blocks/convert 返回的格式转换为 descendant 接口需要的格式
        
        主要转换:
        1. 分析 children 字段建立块之间的层级关系
        2. 找出真正的顶级块（不被任何其他块引用的块）
        3. 为所有块生成新的临时ID
        4. 构建 descendants 列表（所有块）和 children_id 列表（仅顶级块）
        
        Returns:
            (descendants, children_id): 所有块的列表和顶级块ID列表
        """
        import uuid
        
        # 第一步：建立原ID到块的映射
        block_map = {}  # 原block_id -> block
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_id = block.get('block_id')
            if block_id:
                block_map[block_id] = block
        
        # 第二步：找出所有被引用的块ID（出现在任何children中的块）
        referenced_ids = set()
        for block in block_map.values():
            children = block.get('children', [])
            if children:
                for child_id in children:
                    if child_id:
                        referenced_ids.add(child_id)
        
        # 第三步：为所有块生成新的临时ID
        id_mapping = {}  # 原block_id -> 新临时ID
        
        def process_block(block) -> Optional[Dict]:
            if not isinstance(block, dict):
                return None
            
            old_id = block.get('block_id', '')
            new_id = str(uuid.uuid4())
            if old_id:
                id_mapping[old_id] = new_id
            
            # 构建新block
            block_type = block.get('block_type')
            if isinstance(block_type, str):
                try:
                    block_type = int(block_type)
                except:
                    pass
            
            new_block = {
                'block_id': new_id,
                'block_type': block_type
            }
            
            # 复制内容字段
            content_fields = ['text', 'heading1', 'heading2', 'heading3', 'heading4', 'heading5',
                            'heading6', 'heading7', 'heading8', 'heading9', 'bullet', 'ordered',
                            'code', 'quote', 'todo', 'image', 'table', 'table_cell', 'divider', 'file']
            for field in content_fields:
                if field in block:
                    new_block[field] = block[field]
            
            # 保留原始 children（后面会映射ID）
            children = block.get('children', [])
            new_block['children'] = [c for c in children if c] if children else []
            
            return new_block
        
        # 第四步：处理所有块
        processed_blocks = {}
        for old_id, block in block_map.items():
            processed = process_block(block)
            if processed:
                processed_blocks[old_id] = processed
        
        # 第五步：映射所有 children ID
        for block in processed_blocks.values():
            if block.get('children'):
                new_children = []
                for child_old_id in block['children']:
                    if child_old_id in id_mapping:
                        new_children.append(id_mapping[child_old_id])
                    # 如果child_old_id不在id_mapping中，说明它不在本次处理的块中，跳过
                block['children'] = new_children
        
        # 第六步：找出顶级块（不被任何其他块引用的块）
        top_level_old_ids = []
        for old_id in block_map.keys():
            if old_id not in referenced_ids:
                top_level_old_ids.append(old_id)
        
        # 第七步：构建结果
        descendants = list(processed_blocks.values())
        children_id = [id_mapping[old_id] for old_id in top_level_old_ids if old_id in id_mapping]
        
        # 调试信息
        if descendants:
            import json
            logger.debug(f"顶级块ID: {children_id[:3]}... (共{len(children_id)}个)")
            logger.debug(f"被引用的块: {list(referenced_ids)[:3]}... (共{len(referenced_ids)}个)")
            logger.debug(f"总块数量: {len(descendants)}")
        
        return descendants, children_id
    
    async def batch_insert_blocks(self, document_id: str, blocks: List[Dict],
                                  parent_block_id: Optional[str] = None) -> bool:
        """
        批量插入文档块
        
        API: POST /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/descendant
        权限: docx:document:write_only
        
        注意事项:
        - 单次最多插入1000个块
        - 需要分批调用
        - 如需对文档根节点创建子块，可将 document_id 填入 block_id 处
        
        Args:
            document_id: 文档ID
            blocks: 块列表（从blocks/convert获取的格式）
            parent_block_id: 父块ID(可选，默认为文档根节点)
            
        Returns:
            是否成功
        """
        headers = await self._get_headers()
        
        # 如果没有指定父块ID，使用document_id作为根节点block_id
        target_block_id = parent_block_id or document_id
        
        # 验证输入
        if not blocks:
            logger.warning("没有blocks需要插入")
            return True
        
        # 检查blocks格式
        if not isinstance(blocks, list):
            raise ValueError(f"blocks必须是列表，实际是 {type(blocks)}")
        
        # 过滤掉非字典项
        valid_blocks = [b for b in blocks if isinstance(b, dict)]
        if not valid_blocks:
            raise ValueError("没有有效的blocks可以插入")
        
        # 转换为descendant接口需要的格式
        descendants, children_id = self._prepare_blocks_for_descendant(valid_blocks)
        
        if not descendants:
            logger.warning("转换后没有有效的blocks需要插入")
            return True
        
        logger.info(f"准备插入 {len(descendants)} 个块到文档 {document_id}，顶级块: {len(children_id)} 个")
        
        # 分批插入（每批最多1000个）
        batch_size = 1000
        for i in range(0, len(descendants), batch_size):
            batch = descendants[i:i+batch_size]
            
            # 构建请求体 - 飞书API格式
            # 注意：descendant接口需要index参数指定插入位置
            json_data = {
                "index": 0,  # 在开头插入
                "children_id": children_id if i == 0 else [],  # 只有第一批需要指定children_id
                "descendants": batch
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                # 飞书API: 创建嵌套块
                # POST /docx/v1/documents/{document_id}/blocks/{block_id}/descendant
                url = f"{self.BASE_URL}/docx/v1/documents/{document_id}/blocks/{target_block_id}/descendant"
                logger.debug(f"批量创建块: {url}, blocks数量={len(batch)}")
                
                # 打印请求体用于调试
                import json
                logger.debug(f"请求体: {json.dumps(json_data, ensure_ascii=False)[:2000]}...")
                
                try:
                    resp = await client.post(
                        url,
                        headers=headers,
                        params={"document_revision_id": -1},  # -1表示最新版本
                        json=json_data
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    if data.get("code") != 0:
                        logger.error(f"批量插入失败: {data}")
                        raise Exception(f"批量插入失败: {data.get('msg', data)}")
                    
                    logger.info(f"已插入第 {i//batch_size + 1} 批，共 {len(batch)} 个块")
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
                    raise
        
        return True
    
    async def get_blocks(self, document_id: str, page_size: int = 500) -> List[Dict]:
        """
        获取文档块
        
        API: GET /open-apis/docx/v1/documents/{document_id}/blocks
        """
        headers = await self._get_headers()
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.BASE_URL}/docx/v1/documents/{document_id}/blocks",
                headers=headers,
                params={"page_size": page_size}
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 0:
                return data["data"].get("items", [])
            else:
                raise Exception(f"获取文档块失败: {data}")
