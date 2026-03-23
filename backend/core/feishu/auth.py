"""
飞书 OAuth 2.0 认证模块
支持 user_access_token 获取和刷新
"""
import httpx
import time
from typing import Optional, Dict, Any, Callable
from loguru import logger

from config import get_config


class FeishuOAuth:
    """飞书 OAuth 2.0 认证管理器"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    AUTH_URL = "https://accounts.feishu.cn/open-apis/authen/v1/authorize"
    TOKEN_URL = "https://open.feishu.cn/open-apis/authen/v2/oauth/token"
    
    def __init__(self):
        self.config = get_config().feishu
        self._user_access_token: Optional[str] = None
        self._token_expire_time: float = 0
        self._refresh_token: Optional[str] = None
        self._refresh_token_expire_time: float = 0
        self._auth_callback: Optional[Callable] = None
        
        # 使用绝对路径确保在任何工作目录下都能找到
        from pathlib import Path
        # token 文件保存在 backend/data/ 目录下
        self._token_file = Path(__file__).parent.parent.parent / "data" / "user_token.json"
        self._load_token()  # 启动时从文件加载 token
    
    def _load_token(self):
        """从文件加载 token"""
        import json
        
        if not self._token_file.exists():
            logger.debug(f"Token 文件不存在: {self._token_file}")
            return
        
        try:
            with open(self._token_file, 'r') as f:
                data = json.load(f)
            
            self._user_access_token = data.get("access_token")
            self._token_expire_time = data.get("expires_at", 0)
            self._refresh_token = data.get("refresh_token")
            self._refresh_token_expire_time = data.get("refresh_expires_at", 0)
            
            if self.is_authorized():
                logger.info(f"已从文件加载 user_access_token (过期时间: {self._token_expire_time})")
            elif self._refresh_token and time.time() < self._refresh_token_expire_time:
                logger.info("access_token 已过期，但 refresh_token 有效，将在首次使用时自动刷新")
            else:
                logger.info("token 已过期，需要重新授权")
                self.clear_token()
        except Exception as e:
            logger.warning(f"加载 token 文件失败: {e}")
    
    def get_authorize_url(self, redirect_uri: str, state: str = "docuflow") -> str:
        """
        获取 OAuth 授权 URL
        
        用户需要在浏览器中打开此 URL 进行授权
        使用最小权限集合，只包含项目实际需要的权限
        包含 offline_access 以获取 refresh_token
        """
        import urllib.parse

        if not (self.config.app_id or "").strip() or not (self.config.app_secret or "").strip():
            raise ValueError("飞书 App ID/App Secret 未配置")
        
        # 项目实际使用的最小权限集合（根据代码分析）
        # Wiki API: 创建空间、创建节点、读取节点、移动文档
        # Drive API: 上传素材、创建导入任务、查询导入结果
        # offline_access: 获取 refresh_token 用于自动刷新
        scopes = [
            "wiki:wiki",                    # 访问知识库基础权限
            "wiki:space:write_only",        # 创建知识空间
            "wiki:node:create",             # 创建知识节点
            "wiki:node:move",               # 移动文档至知识空间
            "wiki:node:read",               # 读取知识节点
            "docs:document.media:upload",   # 上传素材（导入文件）
            "docs:document:import",         # 创建导入任务
            "drive:drive",                  # 访问云空间基础权限
            "offline_access",               # 获取 refresh_token（必须）
        ]
        
        params = {
            "client_id": self.config.app_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes)
        }
        
        query = urllib.parse.urlencode(params)
        return f"{self.AUTH_URL}?{query}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """
        用授权码换取 user_access_token
        
        Args:
            code: 授权码（从回调 URL 中获取）
            redirect_uri: 必须与授权时使用的 redirect_uri 一致
        
        Returns:
            {
                "access_token": "u-xxx",
                "expires_in": 7200,
                "refresh_token": "r-xxx",
                "refresh_token_expires_in": 604800
            }
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/json; charset=utf-8"},
                json={
                    "grant_type": "authorization_code",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_secret,
                    "code": code,
                    "redirect_uri": redirect_uri
                }
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"飞书响应: code={data.get('code')}, keys={list(data.keys())}")
            if data.get('code') != 0:
                logger.error(f"飞书错误详情: {data}")
            
            if data.get("code") == 0:
                # 飞书可能直接返回 token 数据，也可能嵌套在 data 字段里
                if "access_token" in data:
                    token_data = data
                else:
                    token_data = data.get("data", {})
                
                logger.info(f"获取到 token_data: access_token={'有' if token_data.get('access_token') else '无'}, expires_in={token_data.get('expires_in')}")
                
                if not token_data.get("access_token"):
                    raise Exception(f"飞书响应中没有 access_token: {data}")
                    
                self._save_token(token_data)
                logger.info("user_access_token 获取成功")
                return token_data
            else:
                error_msg = data.get("error_description") or data.get("error") or str(data)
                raise Exception(f"获取 token 失败: {error_msg}")
    
    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        使用 refresh_token 刷新 user_access_token
        
        注意: refresh_token 只能使用一次，每次刷新都会返回新的 refresh_token
        """
        if not self._refresh_token:
            raise Exception("没有 refresh_token，需要重新授权")
        
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.TOKEN_URL,
                headers={"Content-Type": "application/json; charset=utf-8"},
                json={
                    "grant_type": "refresh_token",
                    "client_id": self.config.app_id,
                    "client_secret": self.config.app_secret,
                    "refresh_token": self._refresh_token
                }
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("code") == 0:
                token_data = data.get("data", {})
                self._save_token(token_data)
                logger.info("user_access_token 刷新成功")
                return token_data
            else:
                raise Exception(f"刷新 token 失败: {data}")
    
    def _save_token(self, token_data: Dict[str, Any]):
        """保存 token 信息到内存和文件"""
        import json
        import os
        
        self._user_access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 7200)
        self._token_expire_time = time.time() + expires_in - 300  # 提前5分钟过期
        
        # 保存 refresh_token（如果返回了）
        if "refresh_token" in token_data:
            self._refresh_token = token_data.get("refresh_token")
            refresh_expires_in = token_data.get("refresh_token_expires_in", 604800)
            self._refresh_token_expire_time = time.time() + refresh_expires_in - 3600
        
        token_preview = (self._user_access_token[:20] + '...') if self._user_access_token else 'None'
        logger.info(f"Token 已保存到内存: access_token={token_preview}, expires_at={self._token_expire_time}")
        
        # 持久化到文件
        try:
            os.makedirs(str(self._token_file.parent), exist_ok=True)
            with open(self._token_file, 'w') as f:
                json.dump({
                    "access_token": self._user_access_token,
                    "expires_at": self._token_expire_time,
                    "refresh_token": self._refresh_token,
                    "refresh_expires_at": self._refresh_token_expire_time
                }, f)
            logger.info(f"user_access_token 已保存到文件: {self._token_file}")
        except Exception as e:
            logger.error(f"保存 token 到文件失败: {e}")
    
    async def get_user_access_token(self) -> str:
        """
        获取有效的 user_access_token
        
        如果 token 即将过期，会自动刷新
        如果内存中没有 token，会尝试从文件重新加载
        """
        current_time = time.time()
        
        # 检查当前 token 是否有效
        if self._user_access_token and current_time < self._token_expire_time:
            logger.debug(f"使用内存中的 user_access_token (过期时间: {self._token_expire_time})")
            return self._user_access_token
        
        # 内存中没有有效 token，尝试从文件重新加载
        if not self._user_access_token:
            logger.info("内存中没有 token，尝试从文件重新加载...")
            self._load_token()
            
            # 重新检查
            if self._user_access_token and current_time < self._token_expire_time:
                logger.info("从文件加载 token 成功")
                return self._user_access_token
        
        # Token 已过期，尝试刷新
        if self._refresh_token and current_time < self._refresh_token_expire_time:
            logger.info("access_token 已过期，尝试使用 refresh_token 刷新...")
            try:
                await self.refresh_access_token()
                return self._user_access_token
            except Exception as e:
                logger.error(f"刷新 token 失败: {e}")
                # 刷新失败，继续往下走，提示用户重新授权
        
        # 没有有效 token，需要重新授权
        has_access = self._user_access_token is not None
        has_file = self._token_file.exists()
        has_refresh = self._refresh_token is not None
        
        logger.error(f"没有有效的 user_access_token。内存token: {has_access}, 文件: {has_file}, refresh_token: {has_refresh}")
        
        # 根据情况提供具体的错误信息
        if not has_refresh and has_access:
            raise Exception("授权已过期且无刷新令牌。请重新授权（确保勾选'长期访问权限'）")
        elif has_refresh and current_time >= self._refresh_token_expire_time:
            raise Exception("刷新令牌已过期（超过7天）。请重新授权")
        else:
            raise Exception("没有有效的 user_access_token，请先完成 OAuth 授权")
    
    def is_authorized(self) -> bool:
        """检查是否已完成授权"""
        return (
            self._user_access_token is not None and 
            time.time() < self._token_expire_time
        )
    
    def clear_token(self):
        """清除 token（用于登出或重新授权）"""
        import os
        
        self._user_access_token = None
        self._token_expire_time = 0
        self._refresh_token = None
        self._refresh_token_expire_time = 0
        
        # 删除 token 文件
        try:
            if self._token_file.exists():
                self._token_file.unlink()
        except Exception as e:
            logger.warning(f"删除 token 文件失败: {e}")
        
        logger.info("Token 已清除")
    
    def get_token_info(self) -> Dict[str, Any]:
        """获取当前 token 信息（用于前端显示和调试）"""
        current_time = time.time()
        
        access_valid = self._user_access_token is not None and current_time < self._token_expire_time if self._token_expire_time else False
        refresh_valid = self._refresh_token is not None and current_time < self._refresh_token_expire_time if self._refresh_token_expire_time else False
        
        # 计算剩余时间
        access_remaining = max(0, int(self._token_expire_time - current_time)) if self._token_expire_time else 0
        refresh_remaining = max(0, int(self._refresh_token_expire_time - current_time)) if self._refresh_token_expire_time else 0
        
        # 确定状态
        if access_valid:
            status = "valid"
            status_text = "已授权"
        elif refresh_valid:
            status = "expired_refreshable"
            status_text = "已过期（可刷新）"
        elif self._refresh_token and not refresh_valid:
            status = "refresh_expired"
            status_text = "刷新令牌过期（需重新授权）"
        else:
            status = "unauthorized"
            status_text = "未授权"
        
        return {
            "status": status,
            "status_text": status_text,
            "has_access_token": self._user_access_token is not None,
            "access_token_valid": access_valid,
            "access_token_expire": self._token_expire_time,
            "access_token_remaining": access_remaining,
            "has_refresh_token": self._refresh_token is not None,
            "refresh_token_valid": refresh_valid,
            "refresh_token_expire": self._refresh_token_expire_time,
            "refresh_token_remaining": refresh_remaining,
        }


# 全局实例
feishu_oauth = FeishuOAuth()
