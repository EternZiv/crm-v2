"""
Celery beat schedule for the workflow app.
"""

# Standard library imports
from datetime import timedelta

FINLO_BEAT_SCHEDULE = {
    "process-scheduled-workflow-executions": {
        "task": "finlo.contrib.workflow.tasks.process_scheduled_workflow_executions",
        "schedule": timedelta(seconds=60),
    },
}
