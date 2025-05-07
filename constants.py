import os
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', "")
print(GEMINI_API_KEY)
if not GEMINI_API_KEY:
    raise ValueError("没有找到可用的GEMINI_API_KEY. 请先设置环境变量")