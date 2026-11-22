from abc import ABC, abstractmethod


class JobBackend(ABC):
    """
    Run background export jobs; submit() receives the job id once the job is saved.
    """

    @abstractmethod
    def submit(self, job_id):
        """
        Arrange for the job to run.
        """
        raise NotImplementedError
