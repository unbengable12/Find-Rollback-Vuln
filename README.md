# Find-Rollback-Vuln

本项目查找代码回滚导致的重现漏洞

### 启动
#### 1. 克隆当前仓库
```
git clone https://github.com/unbengable12/Find-Rollback-Vuln.git
pip install -r requirements.txt
```
#### 2. 运行脚本
```sh
export GEMINI_API_KEY='<your api key>'

# 生成正向索引
python generate.py -g <github_url> -r <repo_address>
* 两个参数二选一
-g: github 仓库地址
-r: 本地仓库地址

# 生成反向索引
python rollback.py -r <repo_address>
-r: 本地仓库地址

# 运行脚本
python run.py -r <repo_address> -m <model> 
-r: 本地仓库地址
-m: gemini 模型名称
```
结果保存在 `result` 文件夹中

### TODO

* 新增大模型选项
* 优化提示词
