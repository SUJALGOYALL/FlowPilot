from pathlib import Path

import yaml

from app.schemas.workflow import WorkflowDefinitionSchema


class WorkflowLoader:
    def __init__(self, workflows_dir: str | Path):
        self.workflows_dir = Path(workflows_dir)

    def load_workflow(
        self,
        filename: str,
    ) -> WorkflowDefinitionSchema:
        workflow_path = self.workflows_dir / filename

        if not workflow_path.exists():
            raise FileNotFoundError(
                f"Workflow file not found: {workflow_path}"
            )

        with workflow_path.open("r", encoding="utf-8") as file:
            raw_workflow = yaml.safe_load(file)

        if not raw_workflow:
            raise ValueError(
                f"Workflow file is empty: {workflow_path}"
            )

        return WorkflowDefinitionSchema.model_validate(raw_workflow)