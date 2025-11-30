from mangum import Mangum
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Import FastAPI app
from src.app import app as fastapi_app

# WSGI entry point
def application(environ, start_response):
    handler = Mangum(fastapi_app)
    return handler(environ, start_response)
