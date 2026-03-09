from dataclasses import dataclass
from typing import Optional, Any, Dict, Union
from typing import Literal
from agno.run.agent import RunOutputEvent, CustomEvent


@dataclass
class ExternalAgentRunResponseContentEvent(CustomEvent):
    # type:
    #   - content: 出现在正文，delta
    #   - document: 第三方智能体输出，侧边栏，delta
    #   - citation: 引用，取citation中的内容
    # call_id: 必须填写，可以参考webifier如何拿到的tool_call_id
    call_id: str =None
    type: Literal["content", "citation","document"]= "document"
    metadata: Optional[Union[RunOutputEvent]] = None

    def __post_init__(self):
        valid_types = {"content", "citation", "document"}
        if self.type not in valid_types:
            raise ValueError(f"Invalid type: '{self.type}'. Must be one of {valid_types}")

    def __str__(self):
        if self.content:
            return self.content
        return ""