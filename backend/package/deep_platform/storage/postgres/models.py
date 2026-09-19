from datetime import datetime, timezone
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, JSON, Index, Boolean, BigInteger, ForeignKey
import uuid

Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text, default="")
    icon: Mapped[str] = mapped_column(String(32), default="🤖")
    backend_id: Mapped[str] = mapped_column(String(64), default="chatbot")
    system_prompt: Mapped[str] = mapped_column(Text, default="You are a helpful assistant.")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)  # tools, subagents, model
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(128))
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    workdir_path: Mapped[str] = mapped_column(String(512))  # 宿主路径
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    thread_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256), default="New Chat")
    uid: Mapped[str] = mapped_column(String(36), index=True)
    agent_slug: Mapped[str] = mapped_column(String(64), index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_spec: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|deleted
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    thread_id: Mapped[str] = mapped_column(String(128), index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    role: Mapped[str] = mapped_column(String(16))  # user|assistant|tool|system
    content: Mapped[str] = mapped_column(Text, default="")
    delivery_status: Mapped[str] = mapped_column(String(16), default="queued")
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

class AgentRunRequest(Base):
    __tablename__ = "agent_run_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    uid: Mapped[str] = mapped_column(String(36), index=True)
    agent_slug: Mapped[str] = mapped_column(String(64), index=True)
    thread_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="chat")
    channel: Mapped[str] = mapped_column(String(32), default="web")
    queue_policy: Mapped[str] = mapped_column(String(16), default="enqueue")
    status: Mapped[str] = mapped_column(String(16), default="queued")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    input_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dispatched_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    __table_args__ = (Index("idx_req_uid_agent_thread", "uid", "agent_slug", "thread_id"),)

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    uid: Mapped[str] = mapped_column(String(36), index=True)
    agent_slug: Mapped[str] = mapped_column(String(64))
    thread_id: Mapped[str] = mapped_column(String(128), index=True)
    conversation_id: Mapped[str] = mapped_column(String(36))
    run_type: Mapped[str] = mapped_column(String(16), default="chat")
    status: Mapped[str] = mapped_column(String(16), default="pending")
    runtime_scope_id: Mapped[str] = mapped_column(String(128))
    parent_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt: Mapped[int] = mapped_column(BigInteger, default=0)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    output_message_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (Index("idx_run_uid_thread_status", "uid", "thread_id", "status"), Index("idx_run_lease", "lease_expires_at"),)

class ModelProvider(Base):
    __tablename__ = "model_providers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    provider: Mapped[str] = mapped_column(String(32))  # openai|anthropic|...
    api_key: Mapped[str] = mapped_column(String(512), default="")
    base_url: Mapped[str] = mapped_column(String(256), default="")
    models_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
