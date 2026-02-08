from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel,Field

from agent.prompts import *
from agent.states import *

load_dotenv()
user_prompt = "create a simple calculator web application"

prompt = planner_prompt(user_prompt)

llm = ChatGroq(model="openai/gpt-oss-120b")
resp = llm.with_structured_output(Plan).invoke(prompt)
print(resp)