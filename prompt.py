FIND_COMMIT_HASH_PROMPT = '''
我正在分析一个开源项目的 Git 提交历史。

以下数据描述了一个特定提交（称为 commitA）在指定分支上的新增代码行，以及后续版本标签中这些新增内容被回滚（删除或修改）的情况。
特别地，我关注 commitA 中与补丁相关的代码（即修复 bug、解决特定问题或临时调整的代码），并希望识别后续回滚这些补丁代码的提交。

请先根据 commitA 的修复补丁注释，从 commitA 的新增内容中找出对应的代码。
然后，在下方的回滚 commit 中，找到回滚这部分代码的 commit。
最后，用json格式返回结果。

你需要返回一个json格式的数据，包含commitA中的补丁代码和对应回滚的commit hash。

格式样例：
```json
{
  "commitA": {
    "hash": "xxxxxxx",
    "patch_comment": "xxxxxxxx",
    "patched_code": {
      "src/_bentoml_impl/server/app.py": [
        "if self.is_main and media_type == \"application/vnd.bentoml+pickle\":",
        "# Disallow pickle media type for main service for security reasons",
        "raise BentoMLException(",
        "\"Pickle media type is not allowed for main service\",",
        "error_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,"
      ]
    }
  },
  "rollback_commits": [
    {
      "tag": "xxxxx",
      "hash": "xxxxxxx",
      "files": [
        {
            "filename": "src/_bentoml_impl/server/app.py",
            "rolled_back_code": [
                "if self.is_main and media_type == \"application/vnd.bentoml+pickle\":",
                "# Disallow pickle media type for main service for security reasons",
                "raise BentoMLException(",
                "\"Pickle media type is not allowed for main service\",",
                "error_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,"
            ]
        }
      ]
    }
  ]
}
```

'''

GENERATOR_MARKDOWN_REPORTER = '''
我正在分析一个开源项目的 Git 提交历史。
已知在 CommitA 中，开发人员针对特定的安全问题实施了代码修复，然而在之后的提交中，却将 CommitA 所涉及的修复代码进行了回滚。

你需要完成以下分析任务，并生成一份简洁的 Markdown 文档来记录分析结果。

分析任务
1. CommitA补丁代码作用: 仔细研究 CommitA 中的补丁代码，清晰阐述其针对安全问题所采取的修复措施以及达到的预期效果。
2. 回滚原因分析: 分析后续 Commit 中回滚 CommitA 代码的具体原因，可能涉及兼容性问题、引入新的错误等。
3. 替换代码检查: 全面检查后续 Commit 提交的代码，判断是否存在其他代码能够完全替代 CommitA 补丁代码完成安全修复任务。若存在，需详细说明这些替代代码的功能和实现方式；若不存在，需给出简要的利用步骤，以说明该安全问题仍然可能被利用。
4. 总结: 若在任务 3 中找到了能全面完成补丁任务的其他代码，总结部分直接写 “用其他代码完成了补丁任务”；若未找到，简要概括安全问题现状及可能的风险。

Markdown 文档要求
- 内容结构清晰，各任务分析结果明确区分。
- 语言简洁明了，避免冗长复杂的表述。
- 突出任务 3 的分析结果，确保读者能快速了解是否有替代代码完成补丁任务。

CommitA内容
{analysis}

Commit {hash}内容
{content}
'''