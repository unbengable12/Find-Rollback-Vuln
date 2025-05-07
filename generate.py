import os
import subprocess

def generate(repo, auto, number: int=999999999999):
    cur_dir = os.path.abspath(os.path.dirname(__file__))

    if auto:
        command = 'git log --oneline'
        output_file_path = os.path.join(cur_dir, 'commit_id.txt')

        with open(output_file_path, 'w') as f:
            result = subprocess.run(command, shell=True, cwd=repo, stdout=f, stderr=subprocess.PIPE)

        # 检查命令是否成功执行
        if result.returncode == 0:
            print("命令执行成功，输出已保存到", output_file_path)
        else:
            print("命令执行失败，错误信息如下：")
            print(result.stderr.decode("utf-8"))
        
    commit_ids = []
    with open(output_file_path, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            commit_ids.append(line.split(" ")[0])
    
    if not os.path.exists(os.path.join(cur_dir, 'output')):
        os.makedirs(os.path.join(cur_dir, 'output'))
    
    count = 0
    for id in commit_ids:
        output_file = os.path.join(cur_dir, 'output', f"{id[:7]}.txt")
        if not os.path.exists(output_file):
            os.system(f'python {os.path.join(cur_dir, 'rollback.py')} -repo={repo} -commit={id} > {output_file}')
        print(f"{output_file} 创建成功")
        count += 1
        if count >= number:
            break