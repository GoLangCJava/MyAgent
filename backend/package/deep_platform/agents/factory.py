import os
from deep_platform.config import settings
from deep_platform.agents.tools.builtin import ALL_TOOLS

def get_model(model_spec: str|None=None):
    spec=model_spec or settings.DEFAULT_MODEL
    provider, _, model_name = spec.partition(":")
    model_name=model_name or "gpt-4o-mini"
    try:
        if provider in ("openai",""):
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model_name, streaming=True, temperature=0.7)
        elif provider=="anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model_name, streaming=True)
        else:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", streaming=True)
    except Exception as e:
        print(f"Model init failed {e}, fallback mock")
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        return FakeListChatModel(responses=[f"Mock response for {spec}: I am a deep agent. I will plan with todo, then use tools."])

def create_deep_agent_for_run(agent_slug: str, system_prompt: str|None=None, model_spec: str|None=None, thread_id: str|None=None):
    model=get_model(model_spec)
    research_subagent={
        "name":"researcher",
        "description":"Deep research specialist, search and analyze",
        "system_prompt":"You are researcher. Use internet_search to gather info, write findings to /workspace/research.md",
        "tools":[ALL_TOOLS[0]]
    }
    coder_subagent={
        "name":"coder",
        "description":"Coding expert, write files and execute shell",
        "system_prompt":"You are coder. Write code to /workspace, use list_files and read_file to explore.",
        "tools":ALL_TOOLS[1:]
    }
    writer_subagent={
        "name":"writer",
        "description":"Write and summarize",
        "system_prompt":"You are writer. Read files and synthesize final report to /workspace/final.md",
        "tools":[ALL_TOOLS[1], ALL_TOOLS[2], ALL_TOOLS[3]]
    }
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import StateBackend
        backend_dir=os.path.join(settings.WORKSPACE_BASE, thread_id or "default")
        os.makedirs(backend_dir, exist_ok=True)
        try:
            backend=StateBackend(root_dir=backend_dir)
        except Exception:
            backend=None
        kwargs=dict(
            model=model,
            tools=ALL_TOOLS,
            system_prompt=system_prompt or f"You are agent {agent_slug}. Always use todo to plan first, then delegate to subagents via task tool. Workspace at /workspace maps to host {backend_dir}",
            subagents=[research_subagent, coder_subagent, writer_subagent]
        )
        if backend:
            kwargs["backend"]=backend
        agent=create_deep_agent(**kwargs)
        return agent
    except ImportError:
        print("deepagents not installed, fallback to langchain create_agent")
        from langchain.agents import create_agent
        return create_agent(model, tools=ALL_TOOLS, system_prompt=system_prompt or "You are helpful assistant")
    except Exception as e:
        print(f"create_deep_agent failed {e}, fallback")
        from langchain.agents import create_agent
        return create_agent(model, tools=ALL_TOOLS, system_prompt=system_prompt or "You are helpful assistant")
