from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkflowTrigger(BaseModel):
    department: str
    job_title: str


class WorkflowTaskDefinition(BaseModel):
    id: str
    name: str
    type: str

    requires_approval: bool = False
    approval_role: str | None = None

    depends_on: list[str] = Field(default_factory=list)


class WorkflowDefinitionSchema(BaseModel):
    name: str
    version: str
    description: str | None = None

    trigger: WorkflowTrigger

    tasks: list[WorkflowTaskDefinition]

    model_config = ConfigDict(
        extra="forbid",
    )


# ---------------------------------------------------------
# Workflow execution API schemas
# ---------------------------------------------------------


class WorkflowRunCreate(BaseModel):
    employee_id: int
    job_title: str


class WorkflowTaskResponse(BaseModel):
    id: int
    workflow_run_id: int
    task_id: str
    name: str
    task_type: str
    status: str

    requires_approval: bool
    approval_role: str | None

    depends_on: list[str]

    result: str | None

    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class WorkflowRunResponse(BaseModel):
    id: int
    workflow_definition_id: int
    employee_id: int

    status: str

    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    tasks: list[WorkflowTaskResponse] = Field(
        default_factory=list
    )

    model_config = ConfigDict(
        from_attributes=True,
    )


class TaskApprovalResponse(BaseModel):
    id: int
    task_id: str
    status: str
    result: str | None

    model_config = ConfigDict(
        from_attributes=True,
    )