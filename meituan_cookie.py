import json
import os

COOKIE_FILE = os.path.join(os.path.dirname(__file__), "meituan_cookies.json")

def save_cookies(cookies):
    """
    保存美团外卖Cookie到文件
    
    Args:
        cookies: Cookie列表或字符串
    """
    if isinstance(cookies, str):
        # 解析字符串格式的Cookie
        cookie_list = []
        for cookie_str in cookies.split(';'):
            cookie_str = cookie_str.strip()
            if '=' in cookie_str:
                name, value = cookie_str.split('=', 1)
                cookie_list.append({
                    'name': name.strip(),
                    'value': value.strip(),
                    'domain': '.meituan.com',
                    'path': '/'
                })
        cookies = cookie_list
    
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    print(f"Cookie已保存到: {COOKIE_FILE}")

def load_cookies():
    """
    从文件加载美团外卖Cookie
    
    Returns:
        list: Cookie列表
    """
    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def has_cookies():
    """
    检查是否有保存的Cookie
    
    Returns:
        bool: 是否有Cookie
    """
    return os.path.exists(COOKIE_FILE) and len(load_cookies()) > 0

if __name__ == "__main__":
    print("=" * 60)
    print("美团Cookie管理工具")
    print("=" * 60)
    
    print(f"\nCookie文件路径: {COOKIE_FILE}")
    
    if has_cookies():
        cookies = load_cookies()
        print(f"\n当前保存了 {len(cookies)} 个Cookie:")
        for i, cookie in enumerate(cookies[:10]):
            print(f"  [{i+1}] {cookie.get('name', 'unknown')}")
        if len(cookies) > 10:
            print(f"  ... 还有 {len(cookies) - 10} 个Cookie")
    else:
        print("\n当前没有保存Cookie")
    
    print("""
使用方法:
1. 在浏览器中登录美团外卖
2. 打开开发者工具 (F12)
3. 切换到 Console 标签
4. 执行以下代码导出Cookie:
   JSON.stringify(document.cookie.split('; ').map(c => {
       const [name, ...value] = c.split('=');
       return { name: name.trim(), value: value.join('=').trim() };
   }))
5. 复制输出结果，然后运行: python meituan_cookie.py "粘贴的JSON字符串"
""")
    
    import sys
    if len(sys.argv) > 1:
        cookie_str = sys.argv[1]
        try:
            if cookie_str.startswith('['):
                # JSON格式
                cookies = json.loads(cookie_str)
                save_cookies(cookies)
            else:
                # 字符串格式
                save_cookies(cookie_str)
        except Exception as e:
            print(f"保存Cookie出错: {e}")
