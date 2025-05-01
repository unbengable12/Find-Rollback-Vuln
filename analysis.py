import os
import json
import re
from typing import Dict

def parse_commit_file(filepath: str) -> Dict:
    if not os.path.exists(filepath):
        error_msg = f"File not found: {filepath}"
        print(error_msg)
        raise FileNotFoundError(error_msg)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    commit_data = {
        "commit": "",
        "author": "",
        "date": "",
        "message": "",
        "files": []
    }

    idx = 0
    while idx < len(lines):
        line = lines[idx].rstrip('\n')

        if line.startswith("commit "):
            commit_data["commit"] = line.split()[1]

        elif line.startswith("Author:"):
            commit_data["author"] = line.replace("Author: ", "").strip()

        elif line.startswith("Date:"):
            commit_data["date"] = line.replace("Date:", "").strip()
            idx += 1

            # 提取 commit message
            msg_lines = []
            while idx < len(lines):
                msg_line = lines[idx]
                if msg_line.startswith("    "):
                    msg_lines.append(msg_line.strip())
                    idx += 1
                elif msg_line.strip() == "":
                    idx += 1  # 跳过空行
                else:
                    break  # 不再是 message 的一部分

            commit_data["message"] = "\n".join(msg_lines)
            continue


        elif line.startswith("diff --git"):
            match = re.match(r'diff --git a/(.*?) b/(.*?)$', line)
            if match:
                _, file_b = match.groups()
                file_changes = {
                    "filename": file_b,
                    "changes": [],
                }

                idx += 1
                while idx < len(lines) and not lines[idx].startswith("diff --git"):
                    l = lines[idx]
                    if l.startswith('@@'):
                        hunk_info = {
                            "hunk": l.strip(),
                            "additions": [],
                            "deletions": [],
                        }
                        idx += 1
                        while idx < len(lines) and not lines[idx].startswith('@@') and not lines[idx].startswith("diff --git"):
                            code_line = lines[idx]
                            stripped = code_line.strip()

                            if code_line.startswith('+') and not code_line.startswith('+++'):
                                hunk_info["additions"].append(stripped)
                            elif code_line.startswith('-') and not code_line.startswith('---'):
                                hunk_info["deletions"].append(stripped)
                            idx += 1

                        file_changes["changes"].append(hunk_info)
                        continue
                    else:
                        idx += 1

                commit_data["files"].append(file_changes)
                continue

        idx += 1

    return commit_data


if __name__ == "__main__":
    filepath = "/home/lanbigking/Desktop/vuln/BentoML/commit.txt"
    if os.path.exists(filepath):
        parsed = parse_commit_file(filepath)
    else:
        print(f"File not found: {filepath}")
    print({"files": parsed.get('files')})