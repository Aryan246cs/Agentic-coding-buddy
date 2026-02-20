from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from agent.prompts import *
from agent.states import *
from langgraph.constants import END
from langgraph.graph import StateGraph

load_dotenv()

llm = ChatGroq(model="openai/gpt-oss-120b")

# planner plans everything for the prompt, like tech stack, description, features and files that need to be made


def planner_agent(state: dict) -> dict:
    user_prompt = state["user_prompt"]
    resp = llm.with_structured_output(Plan).invoke(planner_prompt(user_prompt))
    if resp is None:
        raise ValueError("Planner did'nt return a valid response.")
    return {"plan": resp}


def architect_agent(state: dict) -> dict:
    plan: Plan = state["plan"]
    resp = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan))
    if resp is None:
        raise ValueError("Architect did'nt return a valid response.")
    resp.plan = plan
    return {"task_plan": resp}


def coder_agent(state: dict) -> dict:
    steps = state["task_plan"].implementation_steps
    current_step_idx = 0
    current_task = steps[current_step_idx]
    user_prompt = f"Task:{current_task.task_description}\n"
    system_prompt = coder_system_prompt()
    resp = llm.invoke(system_prompt + user_prompt)
    return {"code": resp.content}


graph = StateGraph(dict)
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)
graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_edge("coder", END)
graph.set_entry_point("planner")

agent = graph.compile()

user_prompt = "create a simple calculator web application"

result = agent.invoke({"user_prompt": user_prompt})
print(result)
