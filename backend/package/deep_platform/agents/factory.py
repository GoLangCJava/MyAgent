import os
from deep_platform.config import settings
from deep_platform.agents.tools.builtin import ALL_TOOLS

# 兼容 SiliconFlow / Qwen / OpenAI 的 provider 别名, 全部走 OpenAI 兼容接口
OPENAI_COMPATIBLE_PROVIDERS = {"openai", "", "siliconflow", "silicon", "qwen", "deepseek", "moonshot", "zhipu", "yi"}


def _split_spec(spec: str) -> tuple[str, str]:
    """解析 'provider:model'。无冒号时视为纯模型名, provider 取 DEFAULT_MODEL 的 provider。"""
    spec = (spec or "").strip()
    if ":" in spec:
        provider, _, model_name = spec.partition(":")
        return provider.strip().lower(), model_name.strip()
    # 纯模型名, e.g. "Qwen/Qwen2.5-7B-Instruct"
    default_provider, _, _ = (settings.DEFAULT_MODEL or "").partition(":")
    return (default_provider.strip().lower() or "siliconflow"), spec


def get_model(model_spec: str | None = None):
    spec = model_spec or settings.DEFAULT_MODEL
    provider, model_name = _split_spec(spec)
    model_name = model_name or "Qwen/Qwen2.5-7B-Instruct"
    try:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            api_key, _ = settings.resolve_provider_config(provider)
            kwargs = dict(model=model_name, streaming=True)
            if api_key:
                kwargs["api_key"] = api_key
            return ChatAnthropic(**kwargs)
        # OpenAI 兼容接口 (openai / siliconflow / qwen / deepseek ...)
        from langchain_openai import ChatOpenAI
        api_key, base_url = settings.resolve_provider_config(provider)
        kwargs = dict(model=model_name, streaming=True, temperature=0.7)
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)
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
        from deepagents.backends import FilesystemBackend
        backend_dir=os.path.join(settings.WORKSPACE_BASE, thread_id or "default")
        os.makedirs(backend_dir, exist_ok=True)
        try:
            backend=FilesystemBackend(root_dir=backend_dir)
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
