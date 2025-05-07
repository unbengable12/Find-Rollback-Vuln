import json
import subprocess
import re
from analysis import parse_commit_file
import os

def get_filenames(git_commit_json:json) -> set:
    new_set = set()
    for file in git_commit_json:
        new_set.add(file.get('filename'))
    return new_set

def get_fix(repo, commit_hash:str) -> str:
    bentoml_dir = repo
    get_log_command = f'git log -1 --pretty=%B {commit_hash} > log.txt'
    try:
        subprocess.run(get_log_command, cwd=bentoml_dir, check=True, text=True, capture_output=True, shell=True)
        pattern = r'\* fix: (.*)'
        text = ''
        with open(os.path.join(bentoml_dir, 'log.txt')) as f:
            text = "".join(f.readlines())
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        else:
            return "None"
    except subprocess.CalledProcessError as e:
        print("Error executing git show:", e)
    except FileNotFoundError as e:
        print("Directory not found:", e)

def is_commit_exists(repo_path:str, commit_hash:str) -> bool:
    try:
        # 构建 git rev-parse 命令
        command = ['git', '-C', repo_path, 'rev-parse', '--verify', commit_hash]
        # 执行命令
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # 若返回码为 0，说明命令执行成功，commit 存在
        return result.returncode == 0
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False

def get_commit(repo, commit_hash:str) -> json:
    bentoml_dir = repo
    if not is_commit_exists(bentoml_dir, commit_hash):
        return "None"
    # 定义要执行的 git show 命令
    git_show_command = f"git show {commit_hash} > commit.txt"
    # 执行命令并指定工作目录
    try:
        subprocess.run(git_show_command, cwd=bentoml_dir, check=True, text=True, capture_output=True, shell=True)
        return json.loads(json.dumps(parse_commit_file(os.path.join(bentoml_dir, 'commit.txt'))))
    except subprocess.CalledProcessError as e:
        print("Error executing git show:", e)
    except FileNotFoundError as e:
        print("Directory not found:", e)
        
def filter_non_python_files(input_file):
    """
    从 Git 提交历史文件中删除非 .py 后缀的文件记录。
    """
    # 用于匹配文件记录的正则表达式
    file_start_pattern = re.compile(r'^文件:\s+(.+)$')
    # 标记是否在处理非 .py 文件的代码块
    skip_block = False
    # 存储输出内容的列表
    output_lines = []

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        # 检查是否为文件开始行
        file_match = file_start_pattern.match(line.strip())
        if file_match:
            file_path = file_match.group(1).strip()
            # 检查文件是否以 .py 结尾
            if not file_path.endswith('.py'):
                skip_block = True  # 标记为非 .py 文件，跳过后续代码块
            else:
                skip_block = False  # 标记为 .py 文件，保留
                output_lines.append(line)
        else:
            # 如果不在非 .py 文件块中，保留行
            if not skip_block:
                output_lines.append(line)

    return ''.join(output_lines)

def save_file(path:str, filename:str, content: str):
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        with open(os.path.join(path, filename), 'w', encoding='utf-8') as f:
            f.write(content.strip('```markdown').strip('```').strip('markdown'))
        print(f"已保存到 {os.path.join(path, filename)}")
    except Exception as e:
        print(f"保存出错: {e}")
    