import git
import os
from collections import defaultdict
import re
import argparse

# 辅助函数：将行号和代码行分组为连续的块
def group_consecutive_lines(lines):
    if not lines:
        return []
    # 按行号排序
    lines = sorted(lines, key=lambda x: x[0])
    groups = []
    current_group = [lines[0]]  # (line_number, content)
    for current in lines[1:]:
        last_line_number = current_group[-1][0]
        if current[0] == last_line_number + 1:
            current_group.append(current)
        else:
            groups.append(current_group)
            current_group = [current]
    if current_group:
        groups.append(current_group)
    # 转换为 (start_line, end_line, [content]) 格式
    result = []
    for group in groups:
        start_line = group[0][0]
        end_line = group[-1][0]
        contents = [item[1] for item in group]
        result.append((start_line, end_line, contents))
    return result

# 检查仓库路径
repo_path = "/home/lanbigking/Desktop/vuln/BentoML"
if not os.path.exists(repo_path) or not os.path.isdir(repo_path):
    print(f"错误：仓库路径不存在 - {repo_path}")
    exit(1)
if not os.path.exists(os.path.join(repo_path, ".git")):
    print(f"错误：{repo_path} 不是一个Git仓库")
    exit(1)

repo = git.Repo(repo_path)
print(f"仓库路径有效: {repo_path}")

# 定义并验证commitA_hash
parser = argparse.ArgumentParser(description='处理 commit hash 参数')
parser.add_argument('-commit', type=str, help='指定 commit hash')
args = parser.parse_args()
commitA_hash = ""
if args.commit:
    commitA_hash = args.commit
else:
    print('未提供 commit hash 参数，请使用 -commit 指定。')
    exit(0)
try:
    commitA = repo.commit(commitA_hash)
    print(f"commitA 有效: {commitA.hexsha}")
except git.BadName:
    print(f"错误：无效的提交哈希值 - {commitA_hash}")
    exit(1)

# 获取commitA添加的代码，包含行号，仅限.py文件
if not commitA.parents:
    print("commitA 是初始提交")
    diff = repo.git.show(commitA_hash)
else:
    diff = repo.git.diff(f"{commitA_hash}^", commitA_hash)

added_lines = {}
current_file = None
current_line_number = None
line_number_pattern = re.compile(r'@@ -(\d+),\d+ \+(\d+),\d+ @@')
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        current_file = line[6:]
        if current_file.endswith('.py'):  # 只处理 .py 文件
            added_lines[current_file] = []
        else:
            current_file = None  # 非 .py 文件跳过
    elif line_number_match := line_number_pattern.match(line):
        if current_file:  # 确保是 .py 文件
            current_line_number = int(line_number_match.group(2))  # 新文件起始行号
    elif line.startswith('+') and current_file and current_line_number is not None:
        content = line[1:].strip()
        if content:  # 确保非空
            added_lines[current_file].append((current_line_number, content))
            current_line_number += 1
    elif line.startswith(' ') and current_file and current_line_number is not None:
        current_line_number += 1  # 上下文行也增加行号

print("commitA 添加的代码行（仅 .py 文件）:")
for file, lines in added_lines.items():
    print(f"文件: {file}")
    grouped_lines = group_consecutive_lines(lines)
    for start_line, end_line, contents in grouped_lines:
        if start_line == end_line:
            print(f"  {start_line}: {contents[0]}")
        else:
            print(f"  {start_line}-{end_line}:")
            for content in contents:
                print(f"    {content}")

# 检查commitA是否在main分支上
try:
    main_branch = repo.branches["main"]
except IndexError:
    print("错误：main 分支不存在")
    exit(1)
if commitA in main_branch.commit.traverse():
    print("commitA 在 main 分支上")
else:
    print("commitA 不在 main 分支上")
    exit(1)

# 获取commitA之后的所有提交
try:
    commits = list(repo.iter_commits(f"{commitA_hash}..main"))
except git.GitCommandError:
    print("错误：无法获取 commitA 之后的提交")
    exit(1)
print(f"commitA 之后的提交数量: {len(commits)}")

if not commits:
    print("main 分支上没有 commitA 之后的提交")
    exit(0)

# 构建提交到标签的映射
commit_to_tags = defaultdict(list)
for commit in commits:
    try:
        describe_output = repo.git.describe("--contains", commit.hexsha)
        tag = describe_output.split("~")[0].split("^")[0]  # 提取标签名称
        commit_to_tags[commit.hexsha].append(tag)
    except git.GitCommandError:
        pass
for commit_hash in commit_to_tags:
    commit_to_tags[commit_hash].sort()

# 存储每个提交的删除信息，包含行号
commit_deletions = defaultdict(lambda: defaultdict(list))
commit_full_hashes = {}

# 检查后续提交
for commit in commits:
    if not commit.parents:
        print(f"Commit {commit.hexsha[:7]} 是初始提交")
        continue
    short_hash = commit.hexsha[:7]
    commit_full_hashes[short_hash] = commit.hexsha
    parent_hash = commit.parents[0].hexsha
    diff = repo.git.diff(parent_hash, commit.hexsha)
    
    deleted_lines = {}
    current_file = None
    current_line_number = None
    for line in diff.splitlines():
        if line.startswith("--- a/"):
            current_file = line[6:]
            if current_file.endswith('.py'):  # 只处理 .py 文件
                deleted_lines[current_file] = []
            else:
                current_file = None  # 非 .py 文件跳过
        elif line_number_match := line_number_pattern.match(line):
            if current_file:  # 确保是 .py 文件
                current_line_number = int(line_number_match.group(1))  # 旧文件起始行号
        elif line.startswith("-") and current_file and current_line_number is not None:
            content = line[1:].strip()
            if content:  # 确保非空
                deleted_lines[current_file].append((current_line_number, content))
                current_line_number += 1
        elif line.startswith(' ') and current_file and current_line_number is not None:
            current_line_number += 1  # 上下文行也增加行号

    # 检查是否有删除的行与commitA添加的行匹配（基于内容），避免重复
    for file, deleted in deleted_lines.items():
        if file in added_lines:
            matched_added_lines = set()
            for deleted_line_number, deleted_content in deleted:
                for added_line_number, added_content in added_lines[file]:
                    if deleted_content == added_content and (added_line_number, added_content) not in matched_added_lines:
                        commit_deletions[short_hash][file].append((deleted_line_number, deleted_content))
                        matched_added_lines.add((added_line_number, added_content))
                        break

# 整合输出，按标签分组
if not commit_deletions:
    print("没有后续提交删除了commitA添加的代码（.py 文件）")
else:
    tag_to_commits = defaultdict(list)
    untagged_commits = []
    for short_hash, files in commit_deletions.items():
        full_hash = commit_full_hashes.get(short_hash)
        tags = commit_to_tags.get(full_hash, [])
        if tags:
            for tag in tags:
                tag_to_commits[tag].append((short_hash, files))
        else:
            untagged_commits.append((short_hash, files))

    for tag in sorted(tag_to_commits.keys()):
        print(f"Tag {tag}:")
        for short_hash, files in tag_to_commits[tag]:
            tags = commit_to_tags.get(commit_full_hashes.get(short_hash, ""), [])
            tag_display = f" ({', '.join(tags)})" if tags else ""
            print(f"  Commit {short_hash}{tag_display}:")
            for file, lines in files.items():
                print(f"    文件: {file}")
                grouped_lines = group_consecutive_lines(lines)
                for start_line, end_line, contents in grouped_lines:
                    if start_line == end_line:
                        print(f"      - {start_line}: {contents[0]}")
                    else:
                        print(f"      - {start_line}-{end_line}:")
                        for content in contents:
                            print(f"        {content}")

    if untagged_commits:
        print("无标签提交:")
        for short_hash, files in untagged_commits:
            tags = commit_to_tags.get(commit_full_hashes.get(short_hash, ""), [])
            tag_display = f" ({', '.join(tags)})" if tags else ""
            print(f"  Commit {short_hash}{tag_display}:")
            for file, lines in files.items():
                print(f"    文件: {file}")
                grouped_lines = group_consecutive_lines(lines)
                for start_line, end_line, contents in grouped_lines:
                    if start_line == end_line:
                        print(f"      - {start_line}: {contents[0]}")
                    else:
                        print(f"      - {start_line}-{end_line}:")
                        for content in contents:
                            print(f"        {content}")