#!/usr/bin/env python
"""刷新OAuth token"""
import asyncio
import sys
sys.path.insert(0, 'E:\\WorkSoft\\DocuFlow_AI\\DocuFlow_lark_AI\\backend')

from core.feishu.auth import FeishuOAuth

async def refresh():
    auth = FeishuOAuth()
    # 尝试获取token（会自动刷新）
    token = await auth.get_user_access_token()
    if token:
        print(f"✅ Token有效: {token[:20]}...")
        return True
    else:
        print("❌ Token无效，请重新授权")
        return False

if __name__ == "__main__":
    success = asyncio.run(refresh())
    sys.exit(0 if success else 1)
