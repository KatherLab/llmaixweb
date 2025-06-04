from celery import Celery
from celery.exceptions import CeleryError

try:
    Celery("preprocessing", broker="redis://localhost:6379/0")
    print("Celery app initialized successfully.")
except CeleryError as e:
    # Handle the case where Celery cannot connect to the broker
    print(f"Failed to connect to Celery broker: {e}")
    exit(1)

except Exception as e:
    # Handle any other exceptions that may occur during Celery initialization
    print(f"An error occurred while initializing Celery: {e}")
    exit(1)

app: Celery = Celery("preprocessing", broker="redis://localhost:6379/0")


@app.task
def preprocess_file(data):
    """
    A simple Celery task to preprocess data.
    This is a placeholder for actual preprocessing logic.
    """
    # Simulate some work by sleeping
    import time

    time.sleep(10)
    # Here you would add your preprocessing logic
    return f"Processed data: {data}"
