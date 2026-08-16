# FlowPilot 🚀

**FlowPilot** is an AI-powered employee onboarding workflow automation platform designed to orchestrate, execute, and track employee onboarding workflows.

It combines **YAML-based workflow configuration**, **PostgreSQL**, **dependency-aware task execution**, **human approval gates**, and a backend execution engine. The architecture is designed to later integrate **LangGraph, AI agents, and MCP-based tools** for intelligent and external-service task execution.

---

## ✨ Current Capabilities

- YAML-based workflow definitions
- Workflow schema validation
- Workflow loading and resolution
- PostgreSQL workflow registry
- Employee management
- Workflow execution instances
- Runtime task generation
- Dependency-aware task execution
- Parallel-ready task detection
- Task status management
- Human-in-the-loop approval gates
- Approval and resume flow
- Workflow completion tracking
- Async SQLAlchemy database layer
- Dockerized PostgreSQL and Redis infrastructure

---

## 🏗️ Architecture

```text
                    Workflow YAML
                         │
                         ▼
                 Workflow Loader
                         │
                         ▼
                Workflow Resolver
                         │
                         ▼
                Workflow Registry
                         │
                         ▼
                    PostgreSQL
                         │
                         ▼
                  WorkflowDefinition
                         │
                         ▼
                    WorkflowRun
                         │
                         ▼
                   WorkflowTask[]
                         │
                         ▼
              Task Execution Engine
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Pending     Running    Approval
              │          │          │
              │          ▼          ▼
              │       Completed  Waiting
              │                     │
              │               Human Approval
              │                     │
              └─────────────────────▼
                              Resume Execution
```

---

## 🧩 Core Components

### Workflow Configuration

Workflows are defined using YAML files.

```
YAML
  ↓
WorkflowLoader
  ↓
WorkflowResolver
  ↓
Validated Workflow
```

YAML acts as the source of truth for workflow configuration.

### Workflow Registry

The WorkflowRegistry synchronizes validated YAML workflows into PostgreSQL.

```
WorkflowDefinition
        +
WorkflowTaskDefinition[]
```

This allows the execution engine to use database-backed workflow definitions.

### Workflow Execution

A reusable workflow definition is converted into an execution instance for a specific employee.

```
Employee
   ↓
WorkflowDefinition
   ↓
WorkflowRun
   ↓
WorkflowTask[]
```

WorkflowDefinition represents the reusable template, while WorkflowRun represents one employee's actual onboarding execution.

### Dependency Engine

Tasks are executed according to their dependencies.

Example:

```
welcome_email
      ↓
company_account
   ┌──┴───────────┐
   ↓              ↓
slack_access   github_access
                    ↓
            backend_environment
```

A task becomes ready only when all of its dependencies are completed.

### Human Approval

Tasks requiring approval do not automatically complete.

```
READY
  ↓
WAITING_APPROVAL
  ↓
Human Approval
  ↓
RUNNING
  ↓
COMPLETED
```

This enables human-in-the-loop onboarding workflows.

---

## 🗄️ Database Model

The current workflow execution model includes:

```
WorkflowDefinition
        │
        ├── WorkflowTaskDefinition[]
        │
        └── WorkflowRun[]
                 │
                 └── WorkflowTask[]
```

Other application entities include employees and users.

PostgreSQL is used as the primary relational database.

---

## 🛠️ Tech Stack

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker
- Pydantic
- YAML
- AsyncIO

### Planned AI / Agentic Stack

- LangGraph
- LangChain
- LLMs
- MCP
- External service integrations

---

## 🐳 Infrastructure

The development environment uses Docker services including:

- PostgreSQL
- Redis
- Adminer

PostgreSQL is exposed on:

```
localhost:5432
```

Adminer is available through:

```
http://localhost:8080
```

---

## 🔄 Example Workflow

A Backend Engineer onboarding workflow can contain tasks such as:

1. Welcome Email
2. Company Account
3. Slack Access
4. GitHub Access
5. Security Training
6. VPN Access
7. Backend Environment
8. Manager 1:1

Dependencies determine when each task can execute.

For example:

```
Welcome Email
      ↓
Company Account
      ↓
 ┌────┴────┐
 ↓         ↓
Slack     GitHub
           ↓
    Backend Environment
```

---

## 🧠 Future AI Architecture

The deterministic workflow engine forms the foundation for the AI layer.

```
FlowPilot
                       │
              Workflow Engine
                       │
              ┌────────┴────────┐
              ▼                 ▼
       Deterministic Tasks   AI Tasks
                                │
                                ▼
                           LangGraph
                                │
                                ▼
                           AI Agents
                                │
                                ▼
                              MCP
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
             Email          GitHub/Slack    Infrastructure
```

LangGraph will be used where stateful agentic reasoning is actually required, while the deterministic execution engine remains responsible for workflow state, dependencies, persistence, and approvals.

MCP will provide standardized access to external tools and services.

---

## 📌 Project Status

### Completed

- [x] Database foundation
- [x] Employee model
- [x] Workflow YAML configuration
- [x] Workflow loading
- [x] Workflow resolution
- [x] Workflow registry
- [x] PostgreSQL workflow synchronization
- [x] Workflow run creation
- [x] Runtime task creation
- [x] Dependency resolution
- [x] Task execution
- [x] Approval gates
- [x] Approval and resume flow
- [x] Workflow completion tracking

### Next

- [ ] Workflow execution API
- [ ] Workflow status API
- [ ] Approval API
- [ ] Production task executor architecture
- [ ] LangGraph integration
- [ ] AI-powered onboarding tasks
- [ ] MCP tool integrations
- [ ] External service integrations
- [ ] Authentication and authorization
- [ ] Frontend dashboard
- [ ] Observability and monitoring
- [ ] Production deployment

---

## 🎯 Vision

FlowPilot aims to transform employee onboarding from a collection of manual tasks into an intelligent, stateful, and auditable workflow.

Instead of simply using an AI chatbot, FlowPilot combines:

```
Reliable Workflow Execution
          +
Human Approval
          +
AI Agents
          +
External Tools via MCP
          +
Persistent State
```

to create an extensible employee onboarding automation platform.