import os
import sys

# Ensure repository root is on sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from services.orchestrator.api.main import app
from services.orchestrator.graph.engine import engine
from services.payment_service.main import app as payment_app

# Wire in-memory ASGI transport for serverless execution
engine.set_target_app(payment_app)

# Mount payment microservice directly under /payment_service
app.mount("/payment_service", payment_app)
