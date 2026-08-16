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