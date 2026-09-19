from langchain_core.tools import tool
import os, glob, json

@tool
def internet_search(query: str) -> str:
    """Search internet (mock, replace with Tavily/SerpAPI)"""
    return f"[Search Mock] Results for '{query}': LangGraph deepagents is planning+subagents+filesystem framework. Use todo to plan."

@tool
def write_file(path: str, content: str) -> str:
    """Write file to workspace. path like /workspace/report.md or project/file.txt"""
    base=os.getenv("WORKSPACE_BASE","/tmp/workspaces")
    # remove leading /workspace or /
    clean=path.replace("/workspace/","").lstrip("/")
    full=os.path.join(base, "default", clean)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full,"w",encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} chars to {path} (host: {full})"

@tool
def read_file(path: str) -> str:
    """Read file from workspace"""
    base=os.getenv("WORKSPACE_BASE","/tmp/workspaces")
    clean=path.replace("/workspace/","").lstrip("/")
    full=os.path.join(base, "default", clean)
    try:
        with open(full,"r",encoding="utf-8") as f:
            return f.read()[:20000]
    except Exception as e:
        return f"Error reading {path}: {e}"

@tool
def list_files(dir_path: str = "/workspace") -> str:
    """List files in workspace dir"""
    base=os.getenv("WORKSPACE_BASE","/tmp/workspaces")
    clean=dir_path.replace("/workspace/","").lstrip("/")
    full=os.path.join(base, "default", clean) if clean else os.path.join(base,"default")
    try:
        files=glob.glob(os.path.join(full,"*"))
        rel=[os.path.relpath(f, full) for f in files]
        return json.dumps(rel, ensure_ascii=False)
    except Exception as e:
        return f"Error: {e}"

@tool
def execute_shell(command: str) -> str:
    """Execute shell command in sandbox (mock safe)"""
    import subprocess
    # 安全限制: 只允许 ls, cat, pwd, echo
    allowed=("ls","cat","pwd","echo","wc","head","tail")
    if not any(command.strip().startswith(a) for a in allowed):
        return f"Command not allowed for safety: {command}. Allowed: {allowed}"
    try:
        r=subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10, cwd=os.getenv("WORKSPACE_BASE","/tmp/workspaces")+"/default")
        return r.stdout[:5000] + ("\nSTDERR:"+r.stderr[:1000] if r.stderr else "")
    except Exception as e:
        return f"Error: {e}"

ALL_TOOLS=[internet_search, write_file, read_file, list_files, execute_shell]
