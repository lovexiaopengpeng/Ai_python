"""
Coze API 调用模块
"""
import requests
import json
import time


class CozeBot:
    """Coze 机器人调用类"""
    
    def __init__(self):
        """初始化配置"""
        self.base_url = "https://api.coze.cn/v3"
        self.token = "pat_vcDlPW4d6HgpvRL890LQEhMwkaNCeq4aOICrSozLJfoIDKTpemqgq3KpLawTOAHg"
        self.bot_id = "7649684924001648694"
        self.user_id = "123456789"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def chat(self, content: str, user_id: str = None, stream: bool = False) -> dict:
        """
        调用 Coze API 进行对话
        
        Args:
            content: 用户输入的问题或内容
            user_id: 用户 ID（可选，默认使用初始化时的 user_id）
            stream: 是否使用流式响应（可选，默认 False）
        
        Returns:
            dict: API 响应结果
        """
        url = f"{self.base_url}/chat"
        
        # 构建请求体
        payload = {
            "bot_id": self.bot_id,
            "user_id": user_id or self.user_id,
            "stream": stream,
            "additional_messages": [
                {
                    "content_type": "text",
                    "role": "user",
                    "type": "question",
                    "content": content
                }
            ],
            "parameters": {}
        }
        
        try:
            # 发送 POST 请求
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            
            # 解析响应
            result = response.json()
            
            print(f"[DEBUG] Coze API 响应：{result}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Coze API 调用失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
                "data": None
            }
        except Exception as e:
            print(f"[ERROR] 处理响应失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
                "data": None
            }
    
    def get_chat_messages(self, conversation_id: str, chat_id: str) -> dict:
        """
        获取对话消息（用于获取机器人回复）
        使用 GET 请求获取消息
        
        Args:
            conversation_id: 会话 ID
            chat_id: 聊天 ID
        
        Returns:
            dict: 对话消息列表
        """
        # 尝试不同的 API 端点
        urls_to_try = [
            f"{self.base_url}/chat/message",
            f"{self.base_url}/message",
            f"{self.base_url}/chat/retrieve",
        ]
        
        payload = {
            "conversation_id": conversation_id,
            "chat_id": chat_id
        }
        
        for url in urls_to_try:
            try:
                # 尝试 POST 请求
                response = requests.post(url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    result = response.json()
                    print(f"[DEBUG] 对话消息响应 (POST {url}): {result}")
                    return result
            except Exception:
                continue
        
        # 如果 POST 都失败，尝试 GET 请求
        try:
            get_url = f"{self.base_url}/chat/message?conversation_id={conversation_id}&chat_id={chat_id}"
            response = requests.get(get_url, headers=self.headers)
            if response.status_code == 200:
                result = response.json()
                print(f"[DEBUG] 对话消息响应 (GET): {result}")
                return result
        except Exception as e:
            print(f"[DEBUG] GET 请求失败：{e}")
        
        return {
            "code": -1,
            "msg": "所有 API 端点都失败",
            "data": None
        }
    
    def wait_for_completion(self, conversation_id: str, chat_id: str, timeout: int = 30, interval: int = 1) -> dict:
        """
        等待对话完成并获取结果
        
        Args:
            conversation_id: 会话 ID
            chat_id: 聊天 ID
            timeout: 超时时间（秒）
            interval: 轮询间隔（秒）
        
        Returns:
            dict: 最终的对话结果
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 获取消息
            messages_result = self.get_chat_messages(conversation_id, chat_id)
            
            if messages_result.get("code") == 0:
                data = messages_result.get("data", {})
                messages = data.get("items", [])
                
                # 检查是否有 assistant 的回复
                for msg in messages:
                    if msg.get("role") == "assistant" and msg.get("type") == "answer":
                        return {
                            "code": 0,
                            "msg": "success",
                            "data": {
                                "content": msg.get("content", ""),
                                "conversation_id": conversation_id,
                                "chat_id": chat_id,
                                "messages": messages
                            }
                        }
            
            # 等待一段时间后再次检查
            time.sleep(interval)
        
        return {
            "code": -1,
            "msg": "等待超时",
            "data": None
        }
    
    def get_chat_response(self, content: str, user_id: str = None, wait: bool = False) -> str:
        """
        调用 Coze API 并获取回复内容
        
        Args:
            content: 用户输入的问题或内容
            user_id: 用户 ID（可选）
            wait: 是否等待回复完成（目前 Coze v3 API 不支持轮询获取，默认 False）
        
        Returns:
            str: 机器人的回复内容
        """
        # 发起对话
        result = self.chat(content, user_id, stream=False)
        
        if result.get("code") != 0 or not result.get("data"):
            error_msg = result.get("msg", "未知错误")
            return f"调用失败：{error_msg}"
        
        # 获取会话 ID 和聊天 ID
        data = result.get("data", {})
        conversation_id = data.get("conversation_id")
        chat_id = data.get("id")
        status = data.get("status", "unknown")
        
        print(f"[DEBUG] 会话 ID: {conversation_id}, 聊天 ID: {chat_id}, 状态：{status}")
        
        # 返回对话创建成功的信息
        return f"对话已创建 (ID: {chat_id})，机器人正在处理中..."
    
    def chat_with_response(self, content: str, user_id: str = None) -> dict:
        """
        调用 Coze API 并返回完整响应
        
        Args:
            content: 用户输入的问题或内容
            user_id: 用户 ID（可选）
        
        Returns:
            dict: 包含完整回复的字典
        """
        # 发起对话
        chat_result = self.chat(content, user_id, stream=False)
        
        if chat_result.get("code") != 0:
            return chat_result
        
        data = chat_result.get("data", {})
        conversation_id = data.get("conversation_id")
        chat_id = data.get("id")
        
        # 等待回复
        final_result = self.wait_for_completion(conversation_id, chat_id)
        
        if final_result.get("code") == 0:
            return {
                "code": 0,
                "msg": "success",
                "data": {
                    "content": final_result["data"].get("content", ""),
                    "conversation_id": conversation_id,
                    "chat_id": chat_id
                }
            }
        else:
            return final_result


# 便捷函数
def ask_coze(question: str) -> str:
    """
    快速调用 Coze API
    
    Args:
        question: 问题内容
    
    Returns:
        str: 回复内容
    """
    bot = CozeBot()
    return bot.get_chat_response(question)


# 测试代码
if __name__ == "__main__":
    # 测试调用
    bot = CozeBot()
    
    print("=" * 50)
    print("测试 Coze API 调用 - 获取实际回复")
    print("=" * 50)
    
    # 测试 1: 简单对话并获取回复
    print("\n测试 1: 询问'你是谁'并获取回复")
    reply = bot.get_chat_response("你是谁？")
    print(f"机器人回复：{reply}")
    
    # 测试 2: 获取完整响应
    print("\n测试 2: 获取完整响应数据")
    full_response = bot.chat_with_response("你好，介绍一下你自己")
    print(f"完整响应：{json.dumps(full_response, ensure_ascii=False, indent=2)}")
    
    # 测试 3: 使用便捷函数（不等待）
    print("\n测试 3: 使用便捷函数（不等待回复）")
    answer = ask_coze("今天天气怎么样？")
    print(f"回答：{answer}")
