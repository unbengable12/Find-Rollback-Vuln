# Find-Rollback-Vuln

本项目查找代码回滚导致的重现漏洞

### 启动
#### 1. 克隆当前仓库
```
git clone https://github.com/unbengable12/Find-Rollback-Vuln.git
pip install -r requirements.txt
```
#### 2. 运行脚本
```
export GEMINI_API_KEY='<your api key>'
python run.py -g <github_url> -r <repo_name> -m <model> -n <number>

-g: GitHub仓库链接
-r: 仓库名
-m: 模型名称，默认为Gemini-2.0-flash-lite
-n: 查询个数，默认为9999999999999
```
结果保存在 `result` 文件夹中
