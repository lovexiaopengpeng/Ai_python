"""
Coze API 调用模块
"""
import requests
import time


class CozeBot:
    """Coze 机器人调用类"""
    
    def __init__(self):
        """初始化配置"""
        self.base_url = "https://api.coze.cn/v3"
        self.files_url = "https://api.coze.cn/v1/files"
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
        获取对话消息列表（查看对话消息详情接口）
        
        Args:
            conversation_id: 会话 ID
            chat_id: 聊天 ID
        
        Returns:
            dict: 对话消息列表
        """
        url = f"{self.base_url}/chat/message/list"
        params = {
            "conversation_id": conversation_id,
            "chat_id": chat_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] 对话消息响应：{result}")
            return result
        except Exception as e:
            print(f"[ERROR] 获取对话消息失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
                "data": None
            }
    
    def get_chat_detail(self, conversation_id: str, chat_id: str) -> dict:
        """
        获取对话详情（查看对话详情接口）
        
        Args:
            conversation_id: 会话 ID
            chat_id: 聊天 ID
        
        Returns:
            dict: 对话详情
        """
        url = f"{self.base_url}/chat/retrieve"
        params = {
            "conversation_id": conversation_id,
            "chat_id": chat_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] 对话详情响应：{result}")
            return result
        except Exception as e:
            print(f"[ERROR] 获取对话详情失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
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
            # 先查看对话详情，检查状态
            detail_result = self.get_chat_detail(conversation_id, chat_id)
            
            if detail_result.get("code") == 0:
                data = detail_result.get("data", {})
                status = data.get("status", "")
                
                print(f"[DEBUG] 对话状态：{status}")
                
                # 检查是否为终态
                if status in ["completed", "required_action", "canceled", "failed"]:
                    print(f"[DEBUG] 对话已达到终态：{status}")
                    
                    # 获取消息列表
                    messages_result = self.get_chat_messages(conversation_id, chat_id)
                    
                    if messages_result.get("code") == 0:
                        # messages_data 可能是列表或字典
                        messages_data = messages_result.get("data", {})
                        
                        # 如果是列表，直接使用；如果是字典，获取 items
                        if isinstance(messages_data, list):
                            messages = messages_data
                        else:
                            messages = messages_data.get("items", [])
                        
                        # 查找 assistant 的回复
                        for msg in messages:
                            if msg.get("role") == "assistant" and msg.get("type") == "answer":
                                return {
                                    "code": 0,
                                    "msg": "success",
                                    "data": {
                                        "content": msg.get("content", ""),
                                        "conversation_id": conversation_id,
                                        "chat_id": chat_id,
                                        "status": status,
                                        "messages": messages
                                    }
                                }
                        
                        # 如果没有找到 answer 类型的消息，返回所有消息
                        return {
                            "code": 0,
                            "msg": "success",
                            "data": {
                                "conversation_id": conversation_id,
                                "chat_id": chat_id,
                                "status": status,
                                "messages": messages
                            }
                        }
                    else:
                        return messages_result
            
            # 等待一段时间后再次检查
            time.sleep(interval)
        
        return {
            "code": -1,
            "msg": "等待超时",
            "data": None
        }
    
    def get_chat_response(self, content: str, user_id: str = None, wait: bool = True) -> str:
        """
        调用 Coze API 并获取回复内容
        
        Args:
            content: 用户输入的问题或内容
            user_id: 用户 ID（可选）
            wait: 是否等待回复完成（默认 True）
        
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
        
        # 如果不等待，直接返回基本信息
        if not wait:
            return f"对话已创建 (ID: {chat_id})，机器人正在处理中..."
        
        # 等待并获取回复
        print(f"[DEBUG] 等待机器人回复...")
        final_result = self.wait_for_completion(conversation_id, chat_id)
        
        if final_result.get("code") == 0 and final_result.get("data"):
            reply_content = final_result["data"].get("content", "")
            if reply_content:
                print(f"[DEBUG] 获取到回复：{reply_content}")
                return reply_content
            else:
                return f"对话完成 (ID: {chat_id})，但未获取到回复内容"
        else:
            return f"等待回复超时或失败：{final_result.get('msg', '')}"
    
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
    
    # ============ 文件管理功能 ============
    
    def upload_file(self, file_path: str, purpose: str = "user_file") -> dict:
        """
        上传文件到 Coze（上传文件接口）
        
        Args:
            file_path: 本地文件路径
            purpose: 文件用途（默认："user_file"）
        
        Returns:
            dict: 上传结果，包含 file_id 等信息
        
        使用说明:
            - 消息中无法直接使用本地文件，需要先上传到扣子编程
            - 上传后可在消息中通过指定 file_id 的方式使用此文件
            - 最大文件大小：512 MB
            - 文件格式：支持图片、文档、PDF 等常见格式
        """
        import os
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                "code": -1,
                "msg": f"文件不存在：{file_path}",
                "data": None
            }
        
        url = f"{self.files_url}/upload"
        
        # 准备文件数据
        files = {
            "file": open(file_path, "rb")
        }
        
        data = {
            "purpose": purpose
        }
        
        # 文件上传不需要 Content-Type header，requests 会自动设置
        upload_headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        try:
            response = requests.post(url, headers=upload_headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] 文件上传响应：{result}")
            return result
        except Exception as e:
            print(f"[ERROR] 文件上传失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
                "data": None
            }
        finally:
            # 确保文件关闭
            if "file" in files:
                files["file"].close()
    
    def get_file_info(self, file_id: str) -> dict:
        """
        查看文件详情（查看文件详情接口）
        
        Args:
            file_id: 文件 ID
        
        Returns:
            dict: 文件详情信息
        
        返回字段说明:
            - id: 文件 ID
            - bytes: 文件大小（字节）
            - content_type: 文件类型
            - file_name: 文件名
            - purpose: 文件用途
            - upload_at: 上传时间
        """
        url = f"{self.files_url}/retrieve"
        params = {
            "file_id": file_id
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[DEBUG] 文件详情响应：{result}")
            return result
        except Exception as e:
            print(f"[ERROR] 获取文件详情失败：{e}")
            return {
                "code": -1,
                "msg": str(e),
                "data": None
        }
    
    def upload_and_get_id(self, file_path: str) -> str:
        """
        上传文件并返回 file_id（便捷方法）
        
        Args:
            file_path: 本地文件路径
        
        Returns:
            str: file_id（上传失败返回 None）
        """
        result = self.upload_file(file_path)
        
        if result.get("code") == 0 and result.get("data"):
            file_id = result["data"].get("id")
            print(f"[DEBUG] 文件上传成功，file_id: {file_id}")
            return file_id
        else:
            error_msg = result.get("msg", "未知错误")
            print(f"[ERROR] 文件上传失败：{error_msg}")
            return None


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


def upload_file_to_coze(file_path: str) -> str:
    """
    快速上传文件到 Coze
    
    Args:
        file_path: 本地文件路径
    
    Returns:
        str: file_id（上传失败返回 None）
    """
    bot = CozeBot()
    return bot.upload_and_get_id(file_path)


def get_coze_file_info(file_id: str) -> dict:
    """
    快速获取文件详情
    
    Args:
        file_id: 文件 ID
    
    Returns:
        dict: 文件详情信息
    """
    bot = CozeBot()
    return bot.get_file_info(file_id)

