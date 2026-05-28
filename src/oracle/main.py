"""Application entry point.

Run with:
    uvicorn oracle.main:app --reload                   # development
    uvicorn oracle.main:app --host 0.0.0.0 --port 8000 # production

Or via Docker:
    docker-compose up app
"""

from oracle.interface.api.app import create_app

# Module-level app instance — required by uvicorn
app = create_app()
