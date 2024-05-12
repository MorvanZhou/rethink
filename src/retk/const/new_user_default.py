from textwrap import dedent

from .languages import LanguageEnum

DEFAULT_USER = {
    "nickname": "rethink",
    "email": "rethink@rethink.run",
    "avatar": "",
}

NEW_USER_DEFAULT_NODES = {
    LanguageEnum.EN.value: [
        dedent("""\
        # How do I record

        I like to record freely and without any restrictions.
        """),
        dedent("""\
        Welcome to Rethink

        Rethink is a Knowledge Management System. You can take node and manage them here.

        Use @ to link between notes. For example [@How do I record](/n/{}) .

        Rethink also supports markdown syntax, for example:

        # My task list

        - [ ] task 1
        - [ ] task 2
        - [x] task 3

        """),
    ],
    LanguageEnum.ZH.value: [
        dedent("""\
        # 我如何记录

        我喜欢自由自在的记录，不受任何限制。
        """),
        dedent("""\
        欢迎使用 Rethink

        Rethink 是一个知识管理系统，你可以在这里记录你的知识，管理你的记录。

        使用 @，你就可以链接任意的记录，创建联想。比如 [@我如何记录](/n/{}) 。

        Rethink 同样也支持 markdown 语法，让你可以记录更丰富的表达。比如：

        # 我的任务清单

        - [ ] 任务 1
        - [ ] 任务 2
        - [x] 任务 3

        """),
    ]
}
