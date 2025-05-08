import subprocess
import hashlib
from collections import defaultdict
import os
import sys
import math
import bitarray
import logging
import time
import argparse
from urllib.parse import urlparse
import shutil

cur_dir = os.path.abspath(os.path.dirname(__file__))
parser = argparse.ArgumentParser(description="命令行参数示例")
parser.add_argument('-g', '--github', type=str, required=False, help='GitHub仓库链接')
parser.add_argument('-r', '--repo', type=str, required=False, help='本地仓库地址')
args = parser.parse_args()

github, repo = args.github, args.repo

if github is None and repo is None:
    print("错误: GitHub 链接和本地仓库地址不能同时为空。")
    exit(1)

if github and repo:
    print("只能输入一个参数")
    exit(1)

if repo:
    if not os.path.exists(repo):
        print("错误: 请输入正确的仓库地址")
        exit(1)

if github:
    path = urlparse(github).path
    repo = os.path.splitext(os.path.basename(path))[0].lower()
    if not repo:
        print("错误: 请输入正确的 Github 仓库链接")
        exit(1)
    repo_dir = os.path.join(cur_dir, 'temp', repo)
    
    clone = True
    if os.path.exists(repo_dir):
        print(f"仓库 '{repo}' 已存在，是否重新 clone?")
        choice = input("请输入 Y/N: ").strip().upper()
        if choice == 'Y':
            print(f"正在删除旧仓库：{repo_dir}")
            shutil.rmtree(repo_dir)
        else:
            print("已取消克隆操作")
            clone = False
    else:
        os.mkdir(repo_dir)
    
    try:
        # 尝试克隆仓库
        if clone:
            subprocess.run(['git', 'clone', github, repo_dir], check=True)
            print(f"已将 {github} 克隆到 {repo_dir}")
    except subprocess.CalledProcessError as e:
        print(f"克隆失败: {e}")
        exit(1)


    
# 设置 Git 仓库路径（修改这里）
REPO_PATH = os.path.join(cur_dir, 'temp', repo)  # ← 请修改为你的仓库路径

# 配置日志
logging.basicConfig(level=logging.DEBUG, filename='rollback_detector.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

class BloomFilter:
    def __init__(self, expected_items, false_positive_rate):
        """Initialize Bloom filter with expected items and false positive rate."""
        self.size = self._optimal_size(expected_items, false_positive_rate)
        self.hash_count = self._optimal_hash_count(expected_items, self.size)
        self.bit_array = bitarray.bitarray(self.size)
        self.bit_array.setall(0)

    def _optimal_size(self, n, p):
        """Calculate optimal bit array size."""
        return int(-(n * math.log(p)) / (math.log(2) ** 2))

    def _optimal_hash_count(self, n, m):
        """Calculate optimal number of hash functions."""
        return max(1, int((m / n) * math.log(2)))

    def _hash(self, item, seed):
        """Generate hash for item with given seed."""
        h = hashlib.sha256((str(seed) + item).encode()).hexdigest()
        return int(h, 16) % self.size

    def add(self, item):
        """Add item to Bloom filter."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = 1

    def __contains__(self, item):
        """Check if item is in Bloom filter."""
        return all(self.bit_array[self._hash(item, i)] for i in range(self.hash_count))

def get_all_commits():
    os.chdir(REPO_PATH)
    commits = subprocess.check_output(['git', 'rev-list', '--reverse', 'HEAD']).decode().splitlines()
    return commits

def get_diff_with_line_numbers(commit_hash):
    """返回每个文件的新增和删除行（含行号）"""
    result = subprocess.run(
        ['git', 'show', commit_hash, '--unified=0', '--pretty=format:', '--no-color'],
        capture_output=True,
        text=True
    )
    lines = result.stdout.splitlines()
    diffs = []

    current_file = None
    old_lineno = None
    new_lineno = None

    for line in lines:
        if line.startswith('+++ b/'):
            current_file = line[6:]
            logging.debug(f"Processing file: {current_file}")
        elif line.startswith('@@'):
            # 格式示例：@@ -1,0 +1,3 @@ 或 @@ -10 +10 @@
            parts = line.split()
            try:
                # 提取旧文件和新文件的起始行号
                old_part = parts[1].split(',')[0][1:] if len(parts) > 1 else ''
                new_part = parts[2].split(',')[0][1:] if len(parts) > 2 else ''
                old_lineno = int(old_part) if old_part and old_part.isdigit() else 0
                new_lineno = int(new_part) if new_part and new_part.isdigit() else 0
                logging.debug(f"Hunk: old_lineno={old_lineno}, new_lineno={new_lineno}")
            except (IndexError, ValueError) as e:
                logging.error(f"Failed to parse hunk line: {line}, error: {e}")
                old_lineno = new_lineno = 0  # 默认值为0以继续处理
                continue
        elif current_file and (old_lineno is not None and new_lineno is not None):
            if line.startswith('+'):
                diffs.append((current_file, '+', new_lineno, line[1:].rstrip()))
                new_lineno += 1
                logging.debug(f"Added line: {line[1:].rstrip()} at {new_lineno}")
            elif line.startswith('-') and not line.startswith('---'):
                diffs.append((current_file, '-', old_lineno, line[1:].rstrip()))
                old_lineno += 1
                logging.debug(f"Deleted line: {line[1:].rstrip()} at {old_lineno}")

    return diffs

def hash_line(line):
    """Generate a string representation for hashing, preserving whitespace."""
    # Use the line as-is (after rstrip) to preserve leading/trailing spaces
    return line.rstrip()

def detect_implicit_rollbacks():
    start_time = time.time()  # 记录开始时间
    logging.info("Starting rollback detection")

    # 获取所有提交（按时间顺序，从最早到最晚）
    commits = get_all_commits()
    
    # 初始化布隆过滤器
    bloom = BloomFilter(expected_items=100000000, false_positive_rate=0.0001)
    
    # 存储添加行信息：hash → [(commit, file_path, line_no, code_line)]
    add_line_map = defaultdict(list)
    # 存储回滚信息：commit → [(rolled_back_commit, file_path, line_no, code_line)]
    rollback_map = defaultdict(list)

    # 确保输出目录存在
    output_dir = os.path.join(cur_dir, 'output', 'index')
    os.makedirs(output_dir, exist_ok=True)

    # 按时间顺序遍历提交，收集添加行并检测回滚
    for commit in commits:
        diffs = get_diff_with_line_numbers(commit)
        for file_path, change_type, line_no, code_line in diffs:
            h = hash_line(code_line)
            # 跳过空行或仅含空白字符的行
            if not h.strip():
                logging.debug(f"Skipping empty/whitespace line in {file_path}:{line_no}")
                continue
            if change_type == '+':
                bloom.add(h)
                add_line_map[h].append((commit, file_path, line_no, code_line))
                logging.debug(f"Added to Bloom: {h} in {file_path}:{line_no}")
            elif change_type == '-':
                if h in bloom:
                    if h in add_line_map:
                        for added_commit, added_file, added_lineno, added_line in add_line_map[h][:]:  # 复制列表以避免修改时迭代问题
                            if added_file == file_path and added_commit != commit:
                                rollback_map[commit].append((added_commit, file_path, added_lineno, added_line))
                                add_line_map[h].remove((added_commit, added_file, added_lineno, added_line))
                                if not add_line_map[h]:
                                    del add_line_map[h]
                                logging.info(f"Rollback detected: {commit} rolled back {added_commit} in {file_path}:{added_lineno}")
                    else:
                        logging.warning(f"Bloom filter hit for {h} but no match in add_line_map")
                else:
                    logging.debug(f"No Bloom filter hit for deleted line: {h} in {file_path}:{line_no}")

    # 将回滚信息写入文件
    for commit, rollback_info in rollback_map.items():
        if rollback_info:
            filename = os.path.join(output_dir, f"{commit[:7]}.txt")
            with open(filename, 'w') as f:
                f.write(f"[Rollback Detected] Commit {commit} rolled back the following code:\n")
                commit_group = defaultdict(lambda: defaultdict(list))
                for added_commit, file_path, line_no, code_line in rollback_info:
                    commit_group[added_commit][file_path].append((line_no, code_line))

                for added_commit in sorted(commit_group.keys()):
                    f.write(f"  Rolled-back Commit: {added_commit}\n")
                    for file_path, lines in sorted(commit_group[added_commit].items()):
                        f.write(f"    File Path: {file_path}\n")
                        lines.sort()
                        merged = []
                        current_range = []
                        for lineno, code in lines:
                            if not current_range:
                                current_range = [(lineno, code)]
                            elif lineno == current_range[-1][0] + 1:
                                current_range.append((lineno, code))
                            else:
                                merged.append(current_range)
                                current_range = [(lineno, code)]
                        if current_range:
                            merged.append(current_range)

                        for group in merged:
                            if len(group) == 1:
                                f.write(f"      Line {group[0][0]}: {repr(group[0][1])}\n")
                            else:
                                line_range = f"{group[0][0]}-{group[-1][0]}"
                                f.write(f"      Lines {line_range}:\n")
                                for _, code in group:
                                    f.write(f"        {repr(code)}\n")
                f.write("\n")

    end_time = time.time()  # 记录结束时间
    execution_time = end_time - start_time
    logging.info(f"Rollback detection completed in {execution_time:.2f} seconds")
    print(f"Execution time: {execution_time:.2f} seconds")

if __name__ == "__main__":
    detect_implicit_rollbacks()