# Find-Rollback-Vuln

本项目查找代码回滚导致的重现漏洞

### 启动
#### 1. 克隆当前仓库
```
git clone https://github.com/unbengable12/Find-Rollback-Vuln.git
pip install -r requirements.txt
```
#### 2. 克隆 bentoml 仓库
```
git clone https://github.com/bentoml/BentoML.git
```
#### 3. 获取 commit
```
cd BentoML/
git log --oneline <tag>
```
可以在 git_log.txt 中查看样例
#### 4. 生成输入文件
```
python generate.py
```
#### 5. 运行脚本
替换 `llm.py` 中的 `gemini_api_key`
```
python run.py
```
结果保存在 `result` 文件夹中