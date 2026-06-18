"""JCVI 子任务 CLI 名称与 argv 规范化"""

# region import
from __future__ import annotations

from dataclasses import dataclass

# endregion


@dataclass(frozen=True)
class JcviSubtask:
    """JCVI 子任务的 CLI 展示与 workflow 映射"""

    name: str
    workflow: str
    title: str
    summary: str


JCVI_SUBTASKS: tuple[JcviSubtask, ...] = (
    JcviSubtask(
        "graphics_synteny",
        "graphics_synteny",
        "共线性图",
        "运行 pairwise MCscan 后调用 JCVI graphics.synteny 出图。",
    ),
    JcviSubtask(
        "graphics_dotplot",
        "graphics_dotplot",
        "点图",
        "运行 pairwise MCscan 后调用 JCVI graphics.dotplot 出图。",
    ),
    JcviSubtask(
        "local_synteny",
        "local_synteny",
        "目标基因局部共线性",
        "围绕参考物种目标基因截取局部窗口并出图，需提供 --target-genes。",
    ),
)

JCVI_SUBTASK_WORKFLOWS = {subtask.name: subtask.workflow for subtask in JCVI_SUBTASKS}
JCVI_SUBTASK_BY_NAME = {subtask.name: subtask for subtask in JCVI_SUBTASKS}


def rewrite_jcvi_subtask_argv(argv: list[str]) -> list[str]:
    """把 `analyze mcscan jcvi <subtask>` 规范化为现有 JCVI 参数模型"""

    if len(argv) < 4 or argv[:3] != ["analyze", "mcscan", "jcvi"]:
        return argv

    workflow = JCVI_SUBTASK_WORKFLOWS.get(argv[3])
    if workflow is None:
        return argv

    rewritten = [*argv[:3], *argv[4:], "--jcvi-subtask", workflow]
    return rewritten

