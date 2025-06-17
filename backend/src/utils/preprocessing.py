from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..dependencies import save_file, get_file
from .. import models


def preprocess_files(
    files: list[models.File],
    client: OpenAI | None = None,
    pdf_backend: str = "pymupdf4llm",
    ocr_backend: str = "ocrmypdf",
    llm_model: str | None = None,
    use_ocr: bool = True,
    force_ocr: bool = False,
    ocr_languages: list[str] | None = None,
    ocr_model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    db_session: Session | None = None,
    project_id: int | None = None,
    preprocessing_task_id: int | None = None,
    output_file: bool = True,
) -> list[str]:
    """
    Preprocess a (pdf) file for LLM usage. Output is extracted text / markdown.

    Parameters
    ----------
    files : list[models.File]
        List of file objects to preprocess.
    client : OpenAI | None
        The OpenAI client instance to use for API calls. If None, a default client will be used.
    base_url : str | None
        The base URL for the OpenAI API. If None, the default OpenAI API URL will be used.
    api_key : str | None
        The API key for the OpenAI client. If None, the default API key will be used.
    pdf_backend : str
        The backend to use for PDF processing. Default is "pymupdf4llm".
    ocr_backend : str
        The backend to use for OCR processing. Default is "ocrmypdf".
    llm_model : str | None
        The LLM model to use for processing. If None, the default model will be used.
    use_ocr : bool
        Whether to use OCR for text extraction. Default is True.
    force_ocr : bool
        Whether to force OCR even if text is already detected. Default is False.
    ocr_languages : list[str] | None
        List of languages to use for OCR. If None, defaults to the languages supported by the OCR backend.
    ocr_model : str | None
        The OCR model to use. If None, the default model will be used.
    db_session : Session | None
        If provided, the database models will be updated automatically.
    project_id : int | None
        If provided, the project ID to associate with the preprocessing task.
    preprocessing_task_id : int | None
        If provided, the ID of the preprocessing task to update with progress.
    output_file : bool
        If True, the preprocessed file will be saved to a file. Default is True.

    Returns:
    -------
    list[str]: A list of preprocessed text or file paths.
    """
    from llmaix import preprocess_file as llmaix_preprocess_file

    if db_session is None:
        results = []
        for file in files:
            file_content = get_file(file.file_uuid)
            result = llmaix_preprocess_file(
                filename=file_content,
                client=client,
                pdf_backend=pdf_backend,
                ocr_backend=ocr_backend,
                llm_model=llm_model,
                use_ocr=use_ocr,
                force_ocr=force_ocr,
                ocr_languages=ocr_languages,
                ocr_model=ocr_model,
                base_url=base_url,
                api_key=api_key,
            )
            results.append(result)
        return results

    assert db_session is not None

    if preprocessing_task_id is not None:
        from ..models.project import PreprocessingTask

        task: PreprocessingTask | None = db_session.execute(
            select(PreprocessingTask).where(
                PreprocessingTask.id == preprocessing_task_id
            )
        ).scalar_one_or_none()
        if task is None:
            raise ValueError(
                f"Preprocessing task with ID {preprocessing_task_id} not found."
            )
        task.status = "in_progress"
        assert project_id is not None, (
            "Project ID must be provided if db_session is used."
        )
        assert task.project_id is not None, "Preprocessing task must have a project ID."
        assert task.project_id == project_id, (
            f"Provided project ID {project_id} does not match the task's project ID {task.project_id}."
        )
        db_session.commit()
    else:
        print(
            "Warning: No database session or preprocessing task ID provided. Progress will not be tracked."
        )

    results: list[str] = []

    for i, file in enumerate(files):
        file_content = get_file(file.file_uuid)
        if output_file:
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                tmp_file_path = Path(tmp_file.name)
                try:
                    result = llmaix_preprocess_file(
                        filename=file_content,
                        client=client,
                        pdf_backend=pdf_backend,
                        ocr_backend=ocr_backend,
                        llm_model=llm_model,
                        use_ocr=use_ocr,
                        force_ocr=force_ocr,
                        ocr_languages=ocr_languages,
                        ocr_model=ocr_model,
                        base_url=base_url,
                        api_key=api_key,
                        output=tmp_file_path,
                    )
                    preprocessed_file_content = tmp_file_path.read_bytes()
                    new_file_name = f"preprocessed_{file.id}.pdf"
                    new_file_uuid = save_file(preprocessed_file_content)

                    file_obj = models.File(
                        project_id=project_id,
                        file_name=new_file_name,
                        file_type=models.FileType.APPLICATION_PDF,
                        file_storage_type=models.FileStorageType.LOCAL
                        if settings.LOCAL_DIRECTORY
                        else models.FileStorageType.S3,
                        file_uuid=new_file_uuid,
                    )
                    db_session.add(file_obj)
                    db_session.commit()
                    db_session.refresh(file_obj)

                    if ocr_backend == "ocrmypdf":
                        preprocessing_method = models.PreprocessingMethod.TESSERACT
                    elif ocr_backend == "surya-ocr":
                        preprocessing_method = models.PreprocessingMethod.SURYA_OCR
                    elif ocr_backend == "doclingvlm":
                        preprocessing_method = models.PreprocessingMethod.VISION_OCR
                    else:
                        raise ValueError("Unsupported OCR backend: {ocr_backend}")

                    document = models.Document(
                        project_id=project_id,
                        original_file_id=file.id,
                        text=result,
                        preprocessing_method=preprocessing_method,
                        preprocessed_file_id=file_obj.id,
                    )
                    db_session.add(document)
                    db_session.commit()
                    db_session.refresh(document)
                    task.documents.append(document)
                    db_session.commit()

                    task.document_ids.append(document.id)
                    project = db_session.execute(
                        select(models.Project).where(models.Project.id == project_id)
                    ).scalar_one_or_none()
                    if project is None:
                        raise ValueError(f"Project with ID {project_id} not found.")
                    project.documents.append(document)
                    db_session.commit()
                except Exception as e:
                    db_session.rollback()
                    raise e
                finally:
                    tmp_file_path.unlink()
        else:
            result = llmaix_preprocess_file(
                filename=file_content,
                client=client,
                pdf_backend=pdf_backend,
                ocr_backend=ocr_backend,
                llm_model=llm_model,
                use_ocr=use_ocr,
                force_ocr=force_ocr,
                ocr_languages=ocr_languages,
                ocr_model=ocr_model,
                base_url=base_url,
                api_key=api_key,
            )

            if ocr_backend == "ocrmypdf":
                preprocessing_method = models.PreprocessingMethod.TESSERACT
            elif ocr_backend == "surya-ocr":
                preprocessing_method = models.PreprocessingMethod.SURYA_OCR
            elif ocr_backend == "doclingvlm":
                preprocessing_method = models.PreprocessingMethod.VISION_OCR
            else:
                raise ValueError("Unsupported OCR backend: {ocr_backend}")

            document = models.Document(
                project_id=project_id,
                original_file_id=file.id,
                text=result,
                preprocessing_method=preprocessing_method,
            )
            db_session.add(document)
            db_session.commit()
            db_session.refresh(document)
            task.documents.append(document)
            db_session.commit()

            task.document_ids.append(document.id)
            project = db_session.execute(
                select(models.Project).where(models.Project.id == project_id)
            ).scalar_one_or_none()
            if project is None:
                raise ValueError(f"Project with ID {project_id} not found.")
            project.documents.append(document)
            db_session.commit()

        results.append(result)

        if db_session is not None and preprocessing_task_id is not None:
            task.progress = (i + 1) / len(files) * 100.0
            task.message = f"Processing file {i + 1}/{len(files)}: {file.file_name}"
            db_session.commit()
            db_session.refresh(task)

            print(f"Progress: {task.progress:.2f}% - {task.message}")

    if db_session is not None and preprocessing_task_id is not None:
        db_session.refresh(task)

        task.status = "completed"
        task.message = "Preprocessing completed successfully."
        task.progress = 100.0
        db_session.commit()

    return results
