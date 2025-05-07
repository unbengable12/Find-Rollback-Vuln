from llm import LLM

import os
import json
from utils import *
from prompt import *

gemini = LLM(model='gemini-2.0-flash-lite')

cur_dir = os.path.abspath(os.path.dirname(__file__))

id_path = f'{cur_dir}/commit_id.txt'
dir = f'{cur_dir}/output/'
output_path = f'{cur_dir}/result/'

# 读取待分析的commitId
ids = []
with open(id_path) as f:
    for line in f.readlines():
        id = line.split(" ")[0]
        ids.append(id[:7])

for id in ids:
    file_path = dir + id + ".txt"
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
    fix = get_fix(id)
    print(fix)
    if fix == 'None':
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
        commit = get_commit(hash)
        if commit == 'None':
            continue
        
        prompt = GENERATOR_MARKDOWN_REPORTER.replace('<analysis>', str(data["commitA"])).replace('<hash>', hash).replace('<content>', str(commit))
        print(f"prompt: \n{prompt}\n")
        res = gemini.prompt(prompt=prompt)
        print(f"res: \n{res}\n")
        
        # 大模型生成中没有找到 “用其他代码完成了补丁任务” 则打印markdown文档
        if res.find("用其他代码完成了补丁任务") == -1:
            save_file(output_path, f"{id}.md", res)
    