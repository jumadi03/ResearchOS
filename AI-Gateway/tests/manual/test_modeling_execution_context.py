from app.modeling.execution.modeling_execution_context import (
    ModelingExecutionContext,
)

#
# Modeling Execution Context
#
context = ModelingExecutionContext(
    execution_id="EXEC-0001",
    stage="modeling",
    status="initialized",
)

print(context)