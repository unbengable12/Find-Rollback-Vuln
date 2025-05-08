from llm import LLM

import os
import json
from utils import *
from prompt import *
import argparse

cur_dir = os.path.abspath(os.path.dirname(__file__))
parser = argparse.ArgumentParser(description="命令行参数示例")
parser.add_argument('-m', '--model', type=str, required=False, help='模型名', default='gemini-2.0-flash-lite', choices=['gemini-2.0-flash-lite', 'gemini-2.0-flash'])
parser.add_argument('-r', '--repo', type=str, required=False, help='本地仓库地址')
args = parser.parse_args()

model, repo = args.model, args.repo

if repo is None:
    print("错误: 请输入本地仓库地址")
    exit(1)
else:
    if not os.path.exists(repo):
        print("错误: 请输入正确的本地仓库地址")
        exit(1)
    if not os.path.exists(os.path.join(repo, '.git')):
        print("错误: 请输入正确的本地仓库地址")
        exit(1)

repo_dir = repo

gemini = LLM(model=model)

id_path = os.path.join(cur_dir, 'commit_id.txt')
input_dir = os.path.join(cur_dir, 'output', 'reverse_index')
output_path = os.path.join(cur_dir, 'result')

input_files = []
for root, dirs, files in os.walk(input_dir):
    for file in files:
        file_path = os.path.join(root, file)
        input_files.append(file_path)

for file_path in input_files:
    if not os.path.exists(file_path):
        print(f"未找到{id}.txt")
        continue
    
    print(file_path)
    # 获取commitA的信息
    commmitA = ''
    with open(file_path, 'r', encoding='utf-8') as f:
        commmitA = ''.join(f.readlines())
    commmitA = commmitA.strip()
    print(commmitA)
    
    # 如果在commit描述中没有查询到 fix 字眼
    if commmitA.find('fix') == -1:
        continue
    # 如果没有回滚情况
    index = commmitA.rfind('rollback_by:')
    if index != -1:
        if index + len('rollback_by:') == len(commmitA):
            continue
        remaining_part = commmitA[index + len('rollback_by:'):]
        if remaining_part.isspace():
            continue
    # 进行第一次分析
    prompt = FIND_COMMIT_HASH_PROMPT.replace('<content>', commmitA)
    print(f"prompt: \n{prompt}\n")

    analysis = gemini.prompt(prompt=prompt).strip('```json').strip('```').strip()
    print(f"analysis: \n{analysis}\n")
    
    try:
        data = json.loads(analysis)
        if not data['fix']:
            continue
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
            save_file(output_path, f"{hash[:7]}.md", res)