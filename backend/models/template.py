"""
模板数据模型
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class TemplateManager:
    """模板管理器 - 支持数据库和JSON文件双存储"""
    
    JSON_FILE = Path(__file__).parent.parent.parent / "data" / "templates.json"
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._loaded = False
    
    async def _ensure_loaded(self):
        """确保数据已加载"""
        if not self._loaded:
            await self.load_templates()
            self._loaded = True
    
    async def load_templates(self) -> Dict[str, Dict]:
        """从JSON文件加载模板"""
        if self.JSON_FILE.exists():
            try:
                with open(self.JSON_FILE, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                    # 确保所有节点都是 folder 类型
                    for template in self._cache.values():
                        self._ensure_all_folder_type(template.get('structure', []))
            except Exception as e:
                print(f"加载模板失败: {e}")
                self._cache = self._get_default_templates()
        else:
            self._cache = self._get_default_templates()
            await self.save_templates()
        
        return self._cache

    def _get_template_sync(self, template_id: str) -> Optional[Dict]:
        """同步获取模板（用于同步调用上下文，避免事件循环嵌套）"""
        if not self._loaded:
            if self.JSON_FILE.exists():
                try:
                    with open(self.JSON_FILE, "r", encoding="utf-8") as f:
                        self._cache = json.load(f)
                        for template in self._cache.values():
                            self._ensure_all_folder_type(template.get("structure", []))
                except Exception:
                    self._cache = self._get_default_templates()
            else:
                self._cache = self._get_default_templates()
            self._loaded = True
        return self._cache.get(template_id)
    
    def _ensure_all_folder_type(self, nodes: List[Dict]):
        """递归确保所有节点都是 folder 类型"""
        for node in nodes:
            node['type'] = 'folder'  # 强制设为 folder
            if 'children' in node and node['children']:
                self._ensure_all_folder_type(node['children'])
    
    async def save_templates(self):
        """保存模板到JSON文件"""
        try:
            with open(self.JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模板失败: {e}")
    
    def _get_default_templates(self) -> Dict[str, Dict]:
        """获取默认模板 - 所有节点都是 folder 类型（知识库文档）"""
        return {
            "product_kb": {
                "id": "product_kb",
                "name": "产品知识库",
                "description": "适用于产品交付和运维团队的知识库结构",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "structure": [
                    {
                        "id": "1",
                        "name": "00-新手入门与团队规范",
                        "type": "folder",
                        "children": [
                            {
                                "id": "1-1",
                                "name": "01-新员工30天学习路径",
                                "type": "folder",
                                "children": [
                                    {"id": "1-1-1", "name": "【置顶】第一天必读：知识库使用指南", "type": "folder"},
                                    {"id": "1-1-2", "name": "第一周：产品入门", "type": "folder"},
                                    {"id": "1-1-3", "name": "第二周：开发环境搭建", "type": "folder"}
                                ]
                            },
                            {
                                "id": "1-2",
                                "name": "02-开发规范与工具",
                                "type": "folder",
                                "children": [
                                    {"id": "1-2-1", "name": "代码规范", "type": "folder"},
                                    {"id": "1-2-2", "name": "Git提交规范", "type": "folder"}
                                ]
                            }
                        ]
                    },
                    {
                        "id": "2",
                        "name": "01-产品知识库",
                        "type": "folder",
                        "children": [
                            {
                                "id": "2-1",
                                "name": "CMP（多云管理平台）",
                                "type": "folder",
                                "children": [
                                    {"id": "2-1-1", "name": "01-交付实施", "type": "folder", "children": [
                                        {"id": "2-1-1-1", "name": "标准部署手册", "type": "folder"},
                                        {"id": "2-1-1-2", "name": "环境要求与检查", "type": "folder"}
                                    ]},
                                    {"id": "2-1-2", "name": "02-二次开发", "type": "folder", "children": [
                                        {"id": "2-1-2-1", "name": "API接口文档", "type": "folder"}
                                    ]}
                                ]
                            }
                        ]
                    }
                ]
            },
            "tech_kb": {
                "id": "tech_kb",
                "name": "技术文档",
                "description": "适用于研发团队的技术文档结构",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "structure": [
                    {
                        "id": "t1",
                        "name": "00-技术规范",
                        "type": "folder",
                        "children": [
                            {"id": "t1-1", "name": "编码规范", "type": "folder"},
                            {"id": "t1-2", "name": "架构设计规范", "type": "folder"}
                        ]
                    },
                    {
                        "id": "t2",
                        "name": "01-开发文档",
                        "type": "folder",
                        "children": [
                            {"id": "t2-1", "name": "后端开发", "type": "folder", "children": [
                                {"id": "t2-1-1", "name": "API设计", "type": "folder"}
                            ]}
                        ]
                    }
                ]
            },
            "hr_kb": {
                "id": "hr_kb",
                "name": "HR知识库",
                "description": "适用于人力资源部门的知识库结构",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "structure": [
                    {
                        "id": "h1",
                        "name": "00-入职指南",
                        "type": "folder",
                        "children": [
                            {"id": "h1-1", "name": "新员工手册", "type": "folder"},
                            {"id": "h1-2", "name": "入职流程", "type": "folder"}
                        ]
                    }
                ]
            }
        }
    
    async def list_templates(self) -> List[Dict]:
        """获取所有模板列表"""
        await self._ensure_loaded()
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t.get("description", ""),
                "created_at": t.get("created_at"),
                "updated_at": t.get("updated_at")
            }
            for t in self._cache.values()
        ]
    
    async def get_template(self, template_id: str) -> Optional[Dict]:
        """获取模板详情"""
        await self._ensure_loaded()
        template = self._cache.get(template_id)
        if template:
            # 确保所有节点都是 folder 类型
            self._ensure_all_folder_type(template.get('structure', []))
        return template
    
    async def create_template(self, data: Dict) -> Dict:
        """创建新模板"""
        await self._ensure_loaded()
        
        template_id = data.get("id") or f"template_{len(self._cache) + 1}"
        now = datetime.now().isoformat()
        
        # 确保结构中的所有节点都是 folder 类型
        structure = data.get("structure", [])
        self._ensure_all_folder_type(structure)
        
        template = {
            "id": template_id,
            "name": data.get("name", "未命名模板"),
            "description": data.get("description", ""),
            "created_at": now,
            "updated_at": now,
            "structure": structure
        }
        
        self._cache[template_id] = template
        await self.save_templates()
        return template
    
    async def update_template(self, template_id: str, data: Dict) -> Optional[Dict]:
        """更新模板"""
        await self._ensure_loaded()
        
        if template_id not in self._cache:
            return None
        
        template = self._cache[template_id]
        template["name"] = data.get("name", template["name"])
        template["description"] = data.get("description", template.get("description", ""))
        if "structure" in data:
            template["structure"] = data["structure"]
            # 确保更新后的结构也是全 folder 类型
            self._ensure_all_folder_type(template["structure"])
        template["updated_at"] = datetime.now().isoformat()
        
        await self.save_templates()
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        await self._ensure_loaded()
        
        if template_id in self._cache:
            del self._cache[template_id]
            await self.save_templates()
            return True
        return False
    
    async def add_node(self, template_id: str, parent_id: Optional[str], node_data: Dict) -> Optional[Dict]:
        """添加节点"""
        await self._ensure_loaded()
        
        if template_id not in self._cache:
            return None
        
        template = self._cache[template_id]
        new_node = {
            "id": node_data.get("id") or f"node_{datetime.now().timestamp()}",
            "name": node_data.get("name", "新节点"),
            "type": "folder",  # 强制设为 folder
            "children": []
        }
        
        if not parent_id:
            # 添加到根级别
            template["structure"].append(new_node)
        else:
            # 递归查找父节点
            self._add_node_recursive(template["structure"], parent_id, new_node)
        
        template["updated_at"] = datetime.now().isoformat()
        await self.save_templates()
        return template
    
    def _add_node_recursive(self, nodes: List[Dict], parent_id: str, new_node: Dict) -> bool:
        """递归添加节点"""
        for node in nodes:
            if node["id"] == parent_id:
                if "children" not in node:
                    node["children"] = []
                node["children"].append(new_node)
                return True
            if "children" in node and node["children"]:
                if self._add_node_recursive(node["children"], parent_id, new_node):
                    return True
        return False
    
    async def update_node(self, template_id: str, node_id: str, data: Dict) -> Optional[Dict]:
        """更新节点"""
        await self._ensure_loaded()
        
        if template_id not in self._cache:
            return None
        
        template = self._cache[template_id]
        updated = self._update_node_recursive(template["structure"], node_id, data)
        
        if updated:
            template["updated_at"] = datetime.now().isoformat()
            await self.save_templates()
        
        return template
    
    def _update_node_recursive(self, nodes: List[Dict], node_id: str, data: Dict) -> bool:
        """递归更新节点"""
        for node in nodes:
            if node["id"] == node_id:
                node["name"] = data.get("name", node["name"])
                # 强制保持 folder 类型
                node["type"] = "folder"
                return True
            if "children" in node and node["children"]:
                if self._update_node_recursive(node["children"], node_id, data):
                    return True
        return False
    
    async def delete_node(self, template_id: str, node_id: str) -> Optional[Dict]:
        """删除节点"""
        await self._ensure_loaded()
        
        if template_id not in self._cache:
            return None
        
        template = self._cache[template_id]
        template["structure"] = self._delete_node_recursive(template["structure"], node_id)
        template["updated_at"] = datetime.now().isoformat()
        
        await self.save_templates()
        return template
    
    def _delete_node_recursive(self, nodes: List[Dict], node_id: str) -> List[Dict]:
        """递归删除节点"""
        result = []
        for node in nodes:
            if node["id"] != node_id:
                if "children" in node and node["children"]:
                    node["children"] = self._delete_node_recursive(node["children"], node_id)
                result.append(node)
        return result
    
    def format_for_llm(self, template_id: str) -> str:
        """格式化为LLM可用的文本格式"""
        template = self._get_template_sync(template_id)
        
        if not template:
            return ""
        
        lines = [f"知识库: {template['name']}"]
        lines.append("")
        
        def build_tree(nodes, indent=0):
            for node in nodes:
                prefix = "  " * indent
                # 全部使用 📄 表示文档（因为都是 folder 类型，代表知识库文档）
                lines.append(f"{prefix}📄 {node.get('name', '未命名')}")
                if "children" in node and node["children"]:
                    build_tree(node["children"], indent + 1)
        
        build_tree(template.get("structure", []))
        return "\n".join(lines)
    
    def get_structure_for_feishu(self, template_id: str) -> List[Dict]:
        """获取用于飞书知识库的文档结构"""
        template = self._get_template_sync(template_id)
        
        if not template:
            return []
        
        # 返回结构，用于创建飞书知识库文档层级
        return template.get("structure", [])


# 全局实例
template_manager = TemplateManager()
