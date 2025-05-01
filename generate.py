import os

cur_dir = os.path.abspath(os.path.dirname(__file__))
commit_ids = []
with open(f'{cur_dir}/commit_id.txt', 'r', encoding='utf-8') as f:
    for line in f.readlines():
        commit_ids.append(line.split(" ")[0])
        
if not os.path.exists(f"{cur_dir}/output"):
    os.makedirs(f"{cur_dir}/output")
            
for id in commit_ids:
    os.system(f'python {cur_dir}/rollback.py -commit={id} > {cur_dir}/output/{id[:7]}.txt')
    print(f"{cur_dir}/output/{id[:7]}.txt.txt创建成功")