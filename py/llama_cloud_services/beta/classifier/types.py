from llama_cloud.types.classify_job_results import ClassifyJobResults
from llama_cloud.types.file_classification import FileClassification
from llama_cloud.types.file import File


class FileClassificationWithFile(FileClassification):
    """
    File classification with file object.
    """

    file: File

    @classmethod
    def from_file_classification(
        cls, file_classification: FileClassification, file: File
    ) -> "FileClassificationWithFile":
        if file_classification.file_id != file.id:
            raise ValueError(
                f"File classification ID {file_classification.id} does not match file ID {file.id}"
            )
        ctor_args = {
            **file_classification.dict(),
            "file": file,
        }
        return cls(**ctor_args)


class ClassifyJobResultsWithFiles(ClassifyJobResults):
    """
    Classify job results with file objects.
    """

    items: list[FileClassificationWithFile]

    @classmethod
    def from_classify_job_results(
        cls, classify_job_results: ClassifyJobResults, files: list[File]
    ) -> "ClassifyJobResultsWithFiles":
        if len(classify_job_results.items) != len(files):
            raise ValueError(
                f"Number of classify job results {len(classify_job_results.items)} does not match number of files {len(files)}"
            )
        # create mapping of file classification result to file object
        file_id_to_file: dict[str, File] = {file.id: file for file in files}
        file_classification_to_file: list[tuple[FileClassification, File]] = []
        for item in classify_job_results.items:
            if item.file_id not in file_id_to_file:
                raise ValueError(
                    f"File classification result {item.id} has file ID {item.file_id} that does not match any provided file ID"
                )
            file_classification_to_file.append((item, file_id_to_file[item.file_id]))

        # create a list of file classification with file objects
        ctor_args = classify_job_results.dict()
        ctor_args["items"] = [
            FileClassificationWithFile.from_file_classification(item, file)
            for item, file in file_classification_to_file
        ]
        return cls(**ctor_args)
