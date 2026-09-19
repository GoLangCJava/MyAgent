AGENT_PRESETS={
    "chatbot": {
        "name":"通用助手",
        "slug":"chatbot",
        "icon":"🤖",
        "description":"通用对话，支持规划和文件",
        "system_prompt":"You are a helpful assistant. Use todo to plan complex tasks, delegate to subagents, and write files to /workspace.",
        "backend_id":"chatbot"
    },
    "research": {
        "name":"深度研究",
        "slug":"research",
        "icon":"🔍",
        "description":"深度研究，搜索+写作",
        "system_prompt":"You are research expert. Always plan with todo, then use researcher subagent to search, writer to synthesize. Output final report to /workspace/report.md",
        "backend_id":"research"
    },
    "coder": {
        "name":"编程助手",
        "slug":"coder",
        "icon":"💻",
        "description":"编程，文件操作",
        "system_prompt":"You are coding assistant. Use todo, list_files to explore, write_file to code, execute_shell to test. Workspace is /workspace.",
        "backend_id":"coder"
    },
    "data-analyst": {
        "name":"数据分析",
        "slug":"data-analyst",
        "icon":"📊",
        "description":"数据分析",
        "system_prompt":"You are data analyst. Plan, read files, write python analysis to /workspace/analysis.py and run it.",
        "backend_id":"coder"
    }
}
