from llm import LLM

import os
import json
from utils import *
from prompt import *
import argparse
from urllib.parse import urlparse
import shutil
from generate import generate

cur_dir = os.path.abspath(os.path.dirname(__file__))

parser = argparse.ArgumentParser(description="命令行参数示例")
parser.add_argument('-g', '--github', type=str, required=False, help='GitHub仓库链接')
parser.add_argument('-r', '--repo', type=str, required=False, help='仓库名')
parser.add_argument('-m', '--model', type=str, required=False, help='模型名', default='gemini-2.0-flash-lite', choices=['gemini-2.0-flash-lite', 'gemini-2.0-flash'])
parser.add_argument('-n', '--number', type=int, required=False, help='检查最近提交的commit数量', default=999999999999)
args = parser.parse_args()

github_url, repo, model, number = args.github, args.repo, args.model, args.number

if github_url is None and repo is None:
    print("错误: GitHub 链接和仓库名不能同时为空。")
    exit(1)

if github_url and repo is None:
    path = urlparse(github_url).path
    repo = os.path.splitext(os.path.basename(path))[0].lower()
    if not repo:
        print("错误: 无法从 GitHub 链接中解析出仓库名。")
        exit(1)

repo_dir = os.path.join(cur_dir, 'temp', repo)

if github_url is None and repo:
    if not os.path.exists(repo_dir):
        print(f"本地仓库 {repo} 不存在")
    print(f"使用本地仓库 {repo_dir}")
    
if github_url:
    temp_dir = os.path.join(cur_dir, 'temp')
    repo_dir = os.path.join(temp_dir, repo)
    
    # 创建 temp 文件夹
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    clone = True
    
    # 仓库已经存在
    if os.path.exists(repo_dir):
        print(f"仓库 '{repo}' 已存在，是否重新 clone?")
        choice = input("请输入 Y/N: ").strip().upper()
        if choice == 'Y':
            print(f"正在删除旧仓库：{repo_dir}")
            shutil.rmtree(repo_dir)
        else:
            print("已取消克隆操作")
            clone = False
    
    try:
        # 尝试克隆仓库
        if clone:
            subprocess.run(['git', 'clone', github_url, repo_dir], check=True)
            print(f"已将 {github_url} 克隆到 {repo_dir}")
    except subprocess.CalledProcessError as e:
        print(f"克隆失败: {e}")
        exit(1)

gemini = LLM(model=model)

id_path = os.path.join(cur_dir, 'commit_id.txt')
dir = os.path.join(cur_dir, 'output')
output_path = os.path.join(cur_dir, 'result')

generate(repo=repo_dir, number=number)

# 读取待分析的commitId
ids = []
with open(id_path) as f:
    count = 0
    for line in f.readlines():
        id = line.split(" ")[0]
        ids.append(id[:7])
        count += 1
        if count >= number:
            break

for id in ids:
    file_path = os.path.join(dir, f"{id}.txt")
    if not os.path.exists(file_path):
        print(f"未找到{id}.txt")
        continue
    print(file_path)
    
    # 获取commitA的回滚信息
    commmitA = ''
    with open(file_path, 'r', encoding='utf-8') as f:
        commmitA = ''.join(f.readlines())
    print(commmitA)
    
    # 后续没有回滚代码
    if commmitA.rfind("没有后续提交删除了commitA添加的代码") != -1:
        continue
    
    # 获取修复补丁注释
    fix = get_fix(repo_dir, id)
    print(fix)
    if fix is None or fix == 'None':
        continue
    
    # 进行第一次分析
    prompt = FIND_COMMIT_HASH_PROMPT.replace('<fix>', fix).replace('<content>', commmitA)
    print(f"prompt: \n{prompt}\n")

    analysis = gemini.prompt(prompt=prompt).strip('```json').strip('```').strip()
    print(f"analysis: \n{analysis}\n")
    
    try:
        data = json.loads(analysis)
    except Exception as e:
        print(f"JSON转化错误：{e}")
        continue
    print(data["commitA"])
    
    # 对后续回滚的commit进行第二次大模型分析
    for r in data["rollback_commits"]:
        hash = r["hash"]
        print(hash)
        if len(hash) > 7:
            hash = hash[:7]
        commit = get_commit(repo_dir, hash)
        if commit == 'None':
            continue
        
        prompt = GENERATOR_MARKDOWN_REPORTER.replace('<analysis>', str(data["commitA"])).replace('<hash>', hash).replace('<content>', str(commit))
        print(f"prompt: \n{prompt}\n")
        res = gemini.prompt(prompt=prompt)
        print(f"res: \n{res}\n")
        
        # 大模型生成中没有找到 “用其他代码完成了补丁任务” 则打印markdown文档
        if res.find("用其他代码完成了补丁任务") == -1:
            save_file(output_path, f"{id}.md", res)
    