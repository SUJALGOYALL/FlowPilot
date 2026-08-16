# The loader answers:
# "Load this specific YAML file."
# But our application will need to answer:
# "This employee is a Frontend Engineer. Which workflow should I use?"\

from pathlib import Path

from app.schemas.workflow import WorkflowDefinitionSchema
from app.services.workflow_loader import WorkflowLoader


class WorkflowResolver:
    WORKFLOW_FILES = {
        "Backend Engineer": "backend_engineer.yaml",
        "Frontend Engineer": "frontend_engineer.yaml",
        "AI/ML Engineer": "ai_ml_engineer.yaml",
        "DevOps Engineer": "devops_engineer.yaml",
    }

    def __init__(self, workflows_dir: str | Path):
        self.loader = WorkflowLoader(workflows_dir)

    def resolve(
        self,
        job_title: str,
    ) -> WorkflowDefinitionSchema:
        filename = self.WORKFLOW_FILES.get(job_title)

        if filename is None:
            raise ValueError(
                f"No onboarding workflow configured for job title: {job_title}"
            )

        workflow = self.loader.load_workflow(filename)

        if workflow.trigger.job_title != job_title:
            raise ValueError(
                f"Workflow trigger mismatch: "
                f"expected '{job_title}', "
                f"got '{workflow.trigger.job_title}'"
            )

        return workflow