from celery import Celery
from celery.exceptions import CeleryError
from openai import OpenAI
from sqlalchemy.orm import Session
from .. import models
from ..utils.preprocessing import preprocess_files

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
def preprocess_file_celery(
    files: list[models.File],
    client: OpenAI | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    pdf_backend: str = "pymupdf4llm",
    ocr_backend: str = "ocrmypdf",
    llm_model: str | None = None,
    use_ocr: bool = True,
    force_ocr: bool = False,
    ocr_languages: list[str] | None = None,
    ocr_model: str | None = None,
    db_session: Session | None = None,
    preprocessing_task_id: int | None = None,
):
    """
    Preprocess a (pdf) file for LLM usage. Output is extracted text / markdown.
    """

    return preprocess_files(
        files=files,
        client=client,
        ocr_backend=ocr_backend,
        pdf_backend=pdf_backend,
        llm_model=llm_model,
        use_ocr=use_ocr,
        force_ocr=force_ocr,
        ocr_languages=ocr_languages,
        ocr_model=ocr_model,
        base_url=base_url,
        api_key=api_key,
        db_session=db_session,
        preprocessing_task_id=preprocessing_task_id,
    )
