from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict


class GraphState(TypedDict):
    message: str


def run_node(state: GraphState) -> GraphState:
    return {"message": state["message"]}


builder = StateGraph(GraphState)
builder.add_node("run_node", run_node)
builder.add_edge(START, "run_node")
builder.add_edge("run_node", END)
graph = builder.compile()

