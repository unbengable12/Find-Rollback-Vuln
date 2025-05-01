from llm import LLM

from analysis import parse_commit_file
import os
import json
import re
from utils import *
from prompt import *

gemini = LLM(model='gemini-2.0-flash-lite')

cur_dir = os.path.abspath(os.path.dirname(__file__))

id_path = f'{cur_dir}/commit_id.txt'
dir = f'{cur_dir}/output/'
output_path = f'{cur_dir}/result/'

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
    commmitA = ''
    with open(file_path, 'r', encoding='utf-8') as f:
        commmitA = ''.join(f.readlines())
    print(commmitA)
    if commmitA.rfind("没有后续提交删除了commitA添加的代码") != -1:
        continue
    fix = get_fix(id).strip() + "\n"
    print(fix)
    if fix == 'None':
        continue
    content = ''
    with open(f'/home/lanbigking/Desktop/test/output/{id}.txt') as f:
        content = ''.join(f.readlines())
        
    prompt = FIND_COMMIT_HASH_PROMPT + f"修复补丁注释为:\n{fix}"  + f"具体内容为:\n{content}"
    print(f"prompt: \n{prompt}\n")

    analysis = gemini.prompt(prompt=prompt).strip('```json').strip('```').strip()
    print(f"analysis: \n{analysis}\n")
    
    try:
        data = json.loads(analysis)
    except Exception as e:
        print(f"JSON转化错误：{e}")
        continue
    print(data["commitA"])
    
    for r in data["rollback_commits"]:
        hash = r["hash"]
        print(hash)
        if len(hash) > 7:
            hash = hash[:7]
        commit = get_commit(hash)
        if commit == 'None':
            continue
        prompt = GENERATOR_MARKDOWN_REPORTER.format(analysis=data["commitA"], hash=hash, content=commit)
        print(prompt)
        res = gemini.prompt(prompt=prompt)
        print(res)
        if res.find("用其他代码完成了补丁任务") == -1:
            save_file(output_path, f"{id}.md", res)
    