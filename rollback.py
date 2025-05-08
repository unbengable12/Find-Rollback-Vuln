import os
import re
import subprocess
from collections import defaultdict
import argparse
import time
# 开始计时
start_time = time.time()

cur_dir = os.path.abspath(os.path.dirname(__file__))
parser = argparse.ArgumentParser(description="命令行参数示例")
parser.add_argument('-r', '--repo', type=str, required=False, help='本地仓库地址')
args = parser.parse_args()

repo = args.repo

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

input_dir = os.path.join(cur_dir, 'output', 'index')
output_dir = os.path.join(cur_dir, 'output', 'reverse_index')
os.makedirs(output_dir, exist_ok=True)

# Data structure to store rollback information
rollback_index = defaultdict(lambda: {
    'description': '',
    'rollback_by': defaultdict(lambda: defaultdict(set)),
    'added_code': defaultdict(list)  # Store added code per file with line numbers
})

# Track processed entries to avoid duplicates
processed_entries = set()

def get_commit_description(commit_id):
    """Retrieve the commit message for a given commit ID."""
    try:
        result = subprocess.run(
            ["git", "show", "-s", "--format=%B", commit_id],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "[description not found]"

def get_added_code(commit_id):
    """Retrieve the new code added in a given commit with line numbers."""
    try:
        result = subprocess.run(
            ["git", "show", "--unified=0", commit_id],
            capture_output=True,
            text=True,
            check=True,
            cwd=repo
        )
        diff_output = result.stdout
        added_code = defaultdict(list)
        current_file = None
        current_line_number = None

        for line in diff_output.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
            elif line.startswith("@@"):
                # Parse line numbers from @@ -x,y +a,b @@
                match = re.search(r'\+(\d+)(?:,\d+)? @@', line)
                if match:
                    current_line_number = int(match.group(1))
            elif line.startswith("+") and current_file and not line.startswith("+++"):
                # Extract added line (remove the leading '+')
                added_line = line[1:].strip()
                if added_line:  # Ignore empty lines
                    added_code[current_file].append((current_line_number, added_line))
                    current_line_number += 1  # Increment for the next added line
        return added_code
    except subprocess.CalledProcessError:
        return defaultdict(list)

# Parse rollback output
for filename in os.listdir(input_dir):
    path = os.path.join(input_dir, filename)
    if not os.path.isfile(path):
        continue

    with open(path, encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f]

    rollback_commit_id = None
    current_commit = None
    current_file = None
    current_lines = []
    line_content = []

    for line in lines:
        if line.startswith("[Rollback Detected] Commit "):
            rollback_commit_id = line.split()[3]
        elif line.strip().startswith("Rolled-back Commit:"):
            # Save any pending content before switching commits
            if current_commit and current_file and current_lines and line_content:
                for ln, content in zip(current_lines, line_content):
                    entry_key = (current_commit, rollback_commit_id, current_file, ln, content)
                    if entry_key not in processed_entries:
                        rollback_index[current_commit]['rollback_by'][rollback_commit_id][current_file].add((ln, content))
                        processed_entries.add(entry_key)
                current_lines = []
                line_content = []
            current_commit = line.split()[-1]
            if not rollback_index[current_commit]['description']:
                rollback_index[current_commit]['description'] = get_commit_description(current_commit)
                rollback_index[current_commit]['added_code'] = get_added_code(current_commit)
        elif line.strip().startswith("File Path:"):
            # Save any pending content before switching files
            if current_commit and current_file and current_lines and line_content:
                for ln, content in zip(current_lines, line_content):
                    entry_key = (current_commit, rollback_commit_id, current_file, ln, content)
                    if entry_key not in processed_entries:
                        rollback_index[current_commit]['rollback_by'][rollback_commit_id][current_file].add((ln, content))
                        processed_entries.add(entry_key)
                current_lines = []
                line_content = []
            current_file = line.strip().split(":", 1)[1].strip()
        elif match := re.match(r"\s*Line(?:s)? (\d+)(?:-(\d+))?:", line):
            # Save any pending content before processing new line numbers
            if current_commit and current_file and current_lines and line_content:
                for ln, content in zip(current_lines, line_content):
                    entry_key = (current_commit, rollback_commit_id, current_file, ln, content)
                    if entry_key not in processed_entries:
                        rollback_index[current_commit]['rollback_by'][rollback_commit_id][current_file].add((ln, content))
                        processed_entries.add(entry_key)
                line_content = []
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            current_lines = list(range(start, end + 1))
        elif line.strip().startswith("'") or line.strip().startswith('"'):
            content = line.strip().strip("'\"")
            line_content.append(content)

    # Save any remaining content after the loop
    if current_commit and current_file and current_lines and line_content:
        for ln, content in zip(current_lines, line_content):
            entry_key = (current_commit, rollback_commit_id, current_file, ln, content)
            if entry_key not in processed_entries:
                rollback_index[current_commit]['rollback_by'][rollback_commit_id][current_file].add((ln, content))
                processed_entries.add(entry_key)

# Write merged results
for commit_id, info in rollback_index.items():
    outpath = os.path.join(output_dir, f"{commit_id[:7]}.txt")
    with open(outpath, "w", encoding="utf-8") as f:
        f.write(f"commit_id: {commit_id}\n")
        f.write("description: |\n")
        for desc_line in info['description'].splitlines():
            f.write(f"  {desc_line}\n")
        f.write("added_code:\n")
        for file, lines in info['added_code'].items():
            f.write(f"  file: {file}\n")
            for lineno, content in sorted(lines):  # Sort by line number
                f.write(f"    line {lineno}: '{content}'\n")
        f.write("rollback_by:\n")
        for rollback_commit, file_lines in info['rollback_by'].items():
            f.write(f"  commit: {rollback_commit}\n")
            for file, lines in file_lines.items():
                f.write(f"    file: {file}\n")
                for lineno, content in sorted(lines):
                    f.write(f"      line {lineno}: '{content}'\n")
                    
# 计算执行时间
execution_time = time.time() - start_time
print('execution_time: {:.2f} seconds'.format(execution_time))