"""
导入文件流程测试
测试内容: 文件上传 -> 导入 -> 移动至知识空间 完整流程
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加backend到路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="DEBUG")


class ImportFlowTest:
    """导入流程测试类"""
    
    def __init__(self):
        self.test_results = []
        
    async def setup(self):
        """测试前准备"""
        from core.feishu.auth import feishu_oauth
        
        # 尝试获取token（会自动刷新过期token）
        try:
            token = await feishu_oauth.get_user_access_token()
            if token:
                logger.info("✅ 已授权，可以继续测试")
                return True
            else:
                logger.error("❌ 未授权，请先完成OAuth授权")
                return False
        except Exception as e:
            logger.error(f"❌ 授权检查失败: {e}")
            return False
    
    async def test_upload_media(self, test_file: str):
        """测试1: 上传素材"""
        from core.feishu.drive_api import drive_api
        
        logger.info("\n" + "="*60)
        logger.info("测试1: 上传素材")
        logger.info("="*60)
        
        try:
            file_token = await drive_api.upload_media(test_file)
            logger.info(f"✅ 上传成功: file_token={file_token}")
            return {"success": True, "file_token": file_token}
        except Exception as e:
            logger.error(f"❌ 上传失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_create_import_task(self, file_token: str, file_extension: str, import_type: str, file_name: str = ""):
        """测试2: 创建导入任务"""
        from core.feishu.drive_api import drive_api
        
        logger.info("\n" + "="*60)
        logger.info("测试2: 创建导入任务")
        logger.info("="*60)
        
        try:
            ticket = await drive_api.create_import_task(
                file_token=file_token,
                file_extension=file_extension,
                import_type=import_type,
                file_name=file_name
            )
            logger.info(f"✅ 导入任务创建成功: ticket={ticket}")
            return {"success": True, "ticket": ticket}
        except Exception as e:
            logger.error(f"❌ 创建导入任务失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_get_import_result(self, ticket: str):
        """测试3: 查询导入结果"""
        from core.feishu.drive_api import drive_api
        
        logger.info("\n" + "="*60)
        logger.info("测试3: 查询导入结果")
        logger.info("="*60)
        
        try:
            result = await drive_api.get_import_task_result(ticket)
            logger.info(f"✅ 查询成功: status={result.get('status')}")
            logger.info(f"   result={result}")
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"❌ 查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_full_import(self, test_file: str):
        """测试4: 完整导入流程"""
        from core.feishu.drive_api import drive_api
        
        logger.info("\n" + "="*60)
        logger.info("测试4: 完整导入流程")
        logger.info("="*60)
        
        try:
            result = await drive_api.import_file(test_file)
            logger.info(f"✅ 导入成功!")
            logger.info(f"   token: {result['token']}")
            logger.info(f"   type: {result['type']}")
            logger.info(f"   title: {result['title']}")
            logger.info(f"   url: {result['url']}")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"❌ 导入失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_move_to_wiki(self, space_id: str, doc_type: str, doc_token: str, parent_token: str = ""):
        """测试5: 移动文档至知识空间"""
        from core.feishu.wiki_api import wiki_api
        
        logger.info("\n" + "="*60)
        logger.info("测试5: 移动文档至知识空间")
        logger.info("="*60)
        
        try:
            result = await wiki_api.move_docs_to_wiki(
                space_id=space_id,
                parent_wiki_token=parent_token,
                obj_type=doc_type,
                obj_token=doc_token
            )
            logger.info(f"✅ 移动成功!")
            logger.info(f"   node_token: {result['node_token']}")
            logger.info(f"   url: {result['url']}")
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"❌ 移动失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_llm_summarize(self, test_file: str):
        """测试6: LLM快速总结"""
        from core.llm.processor import LLMProcessor
        
        logger.info("\n" + "="*60)
        logger.info("测试6: LLM快速总结")
        logger.info("="*60)
        
        try:
            # 读取文件内容
            content = ""
            ext = Path(test_file).suffix.lower()
            if ext in ['.txt', '.md']:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()[:3000]
            else:
                content = f"测试文件: {Path(test_file).name}"
            
            processor = LLMProcessor()
            result = await processor.quick_summarize_file(content, Path(test_file).name)
            
            if result["success"]:
                logger.info(f"✅ 总结成功!")
                logger.info(f"   主题: {result.get('topic')}")
                logger.info(f"   要点: {result.get('points', [])}")
            else:
                logger.warning(f"⚠️ 总结失败: {result.get('error')}")
            
            return result
        except Exception as e:
            logger.error(f"❌ 总结失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def run_all_tests(self):
        """运行所有测试"""
        # 查找测试文件
        test_files = [
            "005-实施模板-计划与运营方案模板-v0.2-20181024.docx",
            "云平台高可用部署规划方案v1.1-20201015.docx"
        ]
        
        test_file = None
        for f in test_files:
            path = Path(__file__).parent.parent / f
            if path.exists():
                test_file = str(path)
                break
        
        if not test_file:
            logger.error("❌ 未找到测试文件，请确保项目根目录有 .docx 文件")
            return
        
        logger.info(f"使用测试文件: {test_file}")
        
        # 检查授权
        if not await self.setup():
            return
        
        # 运行测试
        results = []
        
        # 测试1: 完整导入
        import_result = await self.test_full_import(test_file)
        results.append(("full_import", import_result))
        
        if not import_result["success"]:
            logger.error("导入失败，后续测试跳过")
            self.print_summary(results)
            return
        
        # 测试2: LLM总结
        summary_result = await self.test_llm_summarize(test_file)
        results.append(("llm_summarize", summary_result))
        
        # 测试3: 获取知识空间
        from core.feishu.wiki_api import wiki_api
        spaces = await wiki_api.list_spaces()
        if not spaces:
            logger.error("❌ 没有可用的知识空间")
            return
        
        space_id = spaces[0]["space_id"]
        logger.info(f"使用知识空间: {space_id}")
        
        # 测试4: 移动文档
        move_result = await self.test_move_to_wiki(
            space_id=space_id,
            doc_type=import_result["type"],
            doc_token=import_result["token"],
            parent_token=""
        )
        results.append(("move_to_wiki", move_result))
        
        self.print_summary(results)
    
    def print_summary(self, results):
        """打印测试总结"""
        logger.info("\n" + "="*60)
        logger.info("测试总结")
        logger.info("="*60)
        
        passed = 0
        for name, result in results:
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            logger.info(f"{status} - {name}")
            if not result.get("success"):
                logger.info(f"   错误: {result.get('error', '未知错误')}")
            else:
                passed += 1
        
        logger.info(f"\n总计: {passed}/{len(results)} 通过")


async def main():
    test = ImportFlowTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
