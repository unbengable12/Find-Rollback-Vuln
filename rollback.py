import os
import re
import subprocess
from collections import defaultdict

cur_dir = os.path.abspath(os.path.dirname(__file__))

input_dir = os.path.join(cur_dir, 'output', 'index')
output_dir = os.path.join(cur_dir, 'output', 'reverse_index')
os.makedirs(output_dir, exist_ok=True)

# Data structure to store rollback information
rollback_index = defaultdict(lambda: {
    'description': '',
    'rollback_by': defaultdict(lambda: defaultdict(set))
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
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "[description not found]"

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
        f.write("rollback_by:\n")
        for rollback_commit, file_lines in info['rollback_by'].items():
            f.write(f"  commit: {rollback_commit}\n")
            for file, lines in file_lines.items():
                f.write(f"    file: {file}\n")
                for lineno, content in sorted(lines):
                    f.write(f"      line {lineno}: '{content}'\n")