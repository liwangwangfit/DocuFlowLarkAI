"""
LLM处理器 - 内容清洗、摘要、分类、质量审核
"""
import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from loguru import logger

from config import get_config
from .provider import LLMProviderFactory


class LLMProcessor:
    """LLM内容处理器"""
    
    def __init__(self, provider_name: Optional[str] = None):
        self.config = get_config().llm
        self.provider = LLMProviderFactory.get_provider(provider_name)
    
    async def clean_content(self, content: str) -> Dict[str, Any]:
        """
        内容清洗
        
        1. 修正错别字和语法错误
        2. 统一标题层级格式
        3. 规范化列表符号
        4. 转换表格格式
        5. 删除重复内容
        """
        prompt = f"""你是一个专业的文档处理专家。请对以下文档内容进行清洗和格式化：

【任务要求】
1. 修正明显的错别字和语法错误
2. 统一标题层级格式 (# ## ###)
3. 规范化列表符号 (- 或 1. 2. 3.)
4. 将表格转换为标准Markdown表格格式
5. 删除重复或无关的内容
6. 保持文档原有的结构和逻辑

【输出要求】
- 输出标准Markdown格式
- 不要添加任何解释性文字
- 保留原有的图片引用标记

【待处理内容】
{content[:8000]}  # 限制长度避免超出token限制

【清洗后的内容】
"""
        
        try:
            result = await self.provider.generate(prompt)
            
            return {
                "success": True,
                "content": result["text"],
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "action": "clean"
            }
        except Exception as e:
            logger.error(f"内容清洗失败: {e}")
            return {
                "success": False,
                "content": content,
                "error": str(e),
                "action": "clean"
            }
    
    async def summarize(self, content: str) -> Dict[str, Any]:
        """
        生成摘要
        
        提取关键信息和关键词
        """
        prompt = f"""请对以下文档内容生成摘要和关键词：

【任务要求】
1. 生成一段200字以内的摘要
2. 提取5-10个关键词
3. 识别文档的主要主题

【待处理内容】
{content[:6000]}

【输出格式】
摘要: [摘要内容]
关键词: [关键词1], [关键词2], ...
主题: [主题]
"""
        
        try:
            result = await self.provider.generate(prompt)
            text = result["text"]
            
            # 解析输出
            summary = self._extract_section(text, "摘要")
            keywords = self._extract_section(text, "关键词")
            topic = self._extract_section(text, "主题")
            
            return {
                "success": True,
                "summary": summary,
                "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
                "topic": topic,
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "action": "summarize"
            }
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": "summarize"
            }
    
    async def classify(self, content: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        """
        智能分类
        
        推荐文档应该归属的知识库分类
        """
        # 获取模板结构
        kb_structure = await self._get_kb_structure(template_id)
        
        # 先提取摘要
        summary_result = await self.summarize(content)
        summary = summary_result.get("summary", content[:500])
        keywords = summary_result.get("keywords", [])
        
        prompt = f"""你是一个知识库管理专家。请分析以下文档内容，推荐它应该归属的知识库分类。

【知识库结构】
{kb_structure}

【分类规则】
- 交付实施: 包含部署、安装、环境配置、故障排查等内容
- 二次开发: 包含API、SDK、代码示例、定制化开发等内容
- 解决方案: 包含客户案例、方案设计、最佳实践等内容
- 常见问题: 包含FAQ、错误码、问题排查等内容
- 新手入门: 包含入门指南、快速开始等内容

【待分类文档】
摘要: {summary}
关键词: {', '.join(keywords)}

【输出格式】
推荐路径: [知识库]/[分类]/[子分类]
置信度: [0-100]
理由: [简要说明]
"""
        
        try:
            result = await self.provider.generate(prompt)
            text = result["text"]
            
            path = self._extract_section(text, "推荐路径")
            confidence_str = self._extract_section(text, "置信度")
            reason = self._extract_section(text, "理由")
            
            # 解析置信度
            confidence = 0
            try:
                confidence = int(re.search(r'\d+', confidence_str).group())
            except:
                pass
            
            return {
                "success": True,
                "path": path,
                "confidence": confidence,
                "reason": reason,
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "action": "classify"
            }
        except Exception as e:
            logger.error(f"文档分类失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "path": "未分类",
                "confidence": 0,
                "action": "classify"
            }
    
    async def quality_check(self, content: str) -> Dict[str, Any]:
        """
        质量审核
        
        评分维度：
        1. 格式规范性 (30分)
        2. 内容完整性 (30分)
        3. 逻辑清晰度 (20分)
        4. 可读性 (20分)
        """
        prompt = f"""你是一个文档质量审核专家。请对以下Markdown格式文档进行质量评分。

【评分维度】
1. 格式规范性 (30分): 标题层级、列表、表格格式是否正确
2. 内容完整性 (30分): 是否有缺失章节、断章、乱码
3. 逻辑清晰度 (20分): 结构是否合理、逻辑是否通顺
4. 可读性 (20分): 段落长度适中、重点突出

【待审核内容】
{content[:8000]}

【输出格式】
总评分: [0-100]
各维度得分:
- 格式规范性: [得分]/30
- 内容完整性: [得分]/30
- 逻辑清晰度: [得分]/20
- 可读性: [得分]/20

问题列表:
1. [问题描述] - [建议修改]

是否通过: [是/否]
"""
        
        try:
            result = await self.provider.generate(prompt)
            text = result["text"]
            
            # 解析评分
            total_score = self._extract_score(text, "总评分")
            format_score = self._extract_score(text, "格式规范性")
            completeness_score = self._extract_score(text, "内容完整性")
            logic_score = self._extract_score(text, "逻辑清晰度")
            readability_score = self._extract_score(text, "可读性")
            
            # 判断是否通过
            passed = total_score >= self.config.min_score
            
            # 提取问题列表
            issues = self._extract_issues(text)
            
            return {
                "success": True,
                "score": total_score,
                "passed": passed,
                "details": {
                    "format": format_score,
                    "completeness": completeness_score,
                    "logic": logic_score,
                    "readability": readability_score
                },
                "issues": issues,
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "action": "quality_check"
            }
        except Exception as e:
            logger.error(f"质量审核失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "score": 0,
                "passed": False,
                "action": "quality_check"
            }
    
    async def quick_summarize_file(self, content: str, file_name: str) -> Dict[str, Any]:
        """
        快速总结文件内容（非思考模型，用于导入前）
        
        快速提取文件核心主题和内容概要，不进行深入分析
        """
        # 限制内容长度，确保快速响应
        max_length = 3000
        if len(content) > max_length:
            content = content[:max_length] + "\n...（内容截断）"
        
        prompt = f"""请快速总结以下文件内容，用一句话描述文件主题，再列出3-5个要点。

【文件名】
{file_name}

【文件内容】
{content}

【输出格式】
主题：[一句话描述文件核心主题]
要点：
1. [要点1]
2. [要点2]
3. [要点3]
"""
        
        try:
            # 使用非思考模型，temperature设为0.1确保稳定输出
            result = await self.provider.generate(
                prompt, 
                temperature=0.1,
                max_tokens=500
            )
            
            text = result["text"].strip()
            
            # 提取主题
            topic = ""
            topic_match = re.search(r'主题[：:]\s*(.+?)(?=\n|$)', text)
            if topic_match:
                topic = topic_match.group(1).strip()
            
            # 提取要点
            points = []
            for line in text.split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.\s+', line) or line.startswith('- ') or line.startswith('* '):
                    point = re.sub(r'^\d+\.\s*', '', line)
                    point = re.sub(r'^[-*]\s*', '', point)
                    if point:
                        points.append(point)
            
            return {
                "success": True,
                "summary": text,
                "topic": topic or "未识别主题",
                "points": points[:5],
                "tokens": result.get("usage", {}).get("total_tokens", 0),
                "action": "quick_summarize"
            }
        except Exception as e:
            logger.error(f"快速总结失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "topic": "总结失败",
                "points": [],
                "action": "quick_summarize"
            }
    
    async def decide_mount_node(self, file_summary: str, file_name: str, 
                                template_structure: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        根据文件总结和模板结构，决定最合适的挂载节点
        
        Args:
            file_summary: 文件总结内容
            file_name: 文件名
            template_structure: 模板结构（节点列表，包含path和title）
            
        Returns:
            {
                "node_path": "推荐挂载的节点路径",
                "node_title": "节点标题",
                "reason": "推荐理由"
            }
        """
        # 格式化模板结构
        structure_text = self._format_nodes_for_decision(template_structure)
        
        prompt = f"""你是一个知识库管理专家。请根据文件内容和知识库结构，推荐最合适的挂载节点。

【文件信息】
文件名：{file_name}
文件总结：{file_summary[:500]}

【可选挂载点】
{structure_text}

【任务要求】
1. 分析文件主题与各个挂载点的匹配度
2. 选择最相关的一个挂载点
3. 如果没有完全匹配的，选择最接近的上级分类
4. 只从上述列表中选择，不要创建新节点

【输出格式】
推荐路径：[从列表中选择一个完整路径]
理由：[简要说明为什么选这个路径，50字以内]
"""
        
        max_attempts = 3
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                result = await self.provider.generate(
                    prompt,
                    temperature=0.2,
                    max_tokens=300
                )
                
                text = result["text"]
                
                # 提取推荐路径
                path = ""
                path_match = re.search(r'推荐路径[：:]\s*(.+?)(?=\n|$)', text)
                if path_match:
                    path = path_match.group(1).strip()
                
                # 提取理由
                reason = ""
                reason_match = re.search(r'理由[：:]\s*(.+?)(?=\n|$)', text, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()[:100]
                
                # 验证路径是否有效（简单检查是否包含在结构中）
                valid_path = self._validate_node_path(path, template_structure)
                
                return {
                    "success": bool(valid_path),
                    "node_path": valid_path or "根目录",
                    "node_title": path.split("/")[-1] if "/" in path else path,
                    "reason": reason or "根据文件内容匹配推荐",
                    "tokens": result.get("usage", {}).get("total_tokens", 0),
                    "action": "decide_mount_node"
                }
            except Exception as e:
                last_error = e
                err_text = str(e).lower()
                transient = (
                    "incomplete chunked read" in err_text
                    or "peer closed connection" in err_text
                    or "read timeout" in err_text
                    or "connection reset" in err_text
                    or "remoteprotocolerror" in err_text
                )
                if transient and attempt < max_attempts:
                    logger.warning(f"节点决策网络抖动，第{attempt}次重试: {e}")
                    await asyncio.sleep(0.5 * attempt)
                    continue
                logger.error(f"节点决策失败: {e}")
                break

        return {
            "success": False,
            "error": str(last_error) if last_error else "未知错误",
            "node_path": "根目录",
            "node_title": "根目录",
            "reason": "决策失败，挂载到根目录",
            "action": "decide_mount_node"
        }
    
    def _format_nodes_for_decision(self, nodes: List[Dict[str, Any]]) -> str:
        """格式化节点列表供决策使用"""
        lines = []
        for node in nodes:
            path = node.get("path", node.get("title", "未知"))
            title = node.get("title", "未知")
            node_type = node.get("node_type", "")
            # 只显示文件夹类型的节点作为挂载点
            if node_type == "origin" or not node_type:
                lines.append(f"- {path}")
        return "\n".join(lines[:30])  # 最多显示30个选项
    
    def _validate_node_path(self, path: str, nodes: List[Dict[str, Any]]) -> str:
        """验证路径是否有效，返回有效路径或空字符串"""
        if not path or path == "根目录":
            return ""
        
        # 检查路径是否匹配任一节点
        for node in nodes:
            node_path = node.get("path", "")
            if node_path == path or node_path.endswith(path):
                return node_path
        
        # 如果精确匹配失败，返回原路径（让调用方处理）
        return path
    
    async def double_layer_process(self, content: str) -> Dict[str, Any]:
        """
        双层处理流程
        
        第一层：内容处理（清洗+摘要+分类）
        第二层：质量审核（评分≥70通过，否则返回重处理）
        """
        max_retry = self.config.max_retry
        
        for attempt in range(max_retry):
            logger.info(f"双层处理 - 第{attempt + 1}次尝试")
            
            # 第一层：内容处理
            clean_result = await self.clean_content(content)
            if not clean_result["success"]:
                continue
            
            processed_content = clean_result["content"]
            
            # 第二层：质量审核
            quality_result = await self.quality_check(processed_content)
            
            if quality_result["passed"]:
                # 通过审核，返回结果
                summary_result = await self.summarize(processed_content)
                classify_result = await self.classify(processed_content)
                
                return {
                    "success": True,
                    "content": processed_content,
                    "score": quality_result["score"],
                    "summary": summary_result.get("summary", ""),
                    "keywords": summary_result.get("keywords", []),
                    "classification": classify_result.get("path", ""),
                    "attempts": attempt + 1
                }
            else:
                # 未通过，准备重处理
                logger.warning(f"质量审核未通过，得分: {quality_result['score']}")
                content = processed_content  # 使用已处理的内容继续
        
        # 达到最大重试次数
        return {
            "success": False,
            "error": f"达到最大重试次数({max_retry})，质量审核仍未通过",
            "content": content
        }
    
    async def _get_kb_structure(self, template_id: Optional[str]) -> str:
        """获取知识库结构（异步方法）"""
        # 默认结构
        default_structure = """
00-新手入门与团队规范
  01-新员工30天学习路径
  02-开发规范与工具
  03-项目交付标准流程
  04-常用模板

01-产品知识库
  CMP（多云管理平台）
    01-交付实施
    02-二次开发
    03-解决方案
  MaxKB（知识库工具）
    01-部署与运维
    02-API与集成
    03-常见问题
"""
        
        if not template_id:
            return default_structure
        
        # 从模板管理器加载（异步调用）
        try:
            from models.template import template_manager
            template = await template_manager.get_template(template_id)
            
            if template and template.get('structure'):
                return self._format_structure_for_llm(template['structure'])
        except Exception as e:
            logger.warning(f"加载模板失败: {e}")
        
        return default_structure
    
    def _format_structure_for_llm(self, structure: list, indent: int = 0) -> str:
        """格式化结构为LLM可读的字符串"""
        lines = []
        for node in structure:
            icon = "📁" if node.get('type') == 'folder' else "📄"
            prefix = "  " * indent
            lines.append(f"{prefix}{icon} {node.get('name', '未命名')}")
            
            children = node.get('children', [])
            if children:
                lines.append(self._format_structure_for_llm(children, indent + 1))
        
        return "\n".join(lines)
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """从文本中提取指定部分"""
        pattern = rf'{section_name}[：:]\s*(.+?)(?=\n\w+[：:]|$)'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_score(self, text: str, dimension: str) -> int:
        """提取评分"""
        pattern = rf'{dimension}[：:]\s*(\d+)'
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
        return 0
    
    def _extract_issues(self, text: str) -> List[str]:
        """提取问题列表"""
        issues = []
        in_issues = False
        
        for line in text.split('\n'):
            if '问题列表' in line:
                in_issues = True
                continue
            if in_issues:
                if line.strip().startswith(('1.', '2.', '3.', '-', '*')):
                    issues.append(line.strip())
                elif line.strip() and not line.strip().startswith('是否'):
                    issues.append(line.strip())
        
        return issues[:10]  # 最多返回10个问题
