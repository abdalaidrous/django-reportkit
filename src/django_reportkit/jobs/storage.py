from django.core.files import File
from django.core.files.storage import storages

from ..conf import reportkit_settings


def job_storage():
    """
    Return the storage that keeps finished exports (settings JOB_STORAGE, "default" by default).
    """
    return storages[reportkit_settings.JOB_STORAGE]


def save_export(job, spool):
    """
    Store an export file under JOB_DIRECTORY and return its storage name.
    """
    return job_storage().save(f"{reportkit_settings.JOB_DIRECTORY}/{job.pk}/{job.filename}", File(spool, name=job.filename))


def delete_export(name):
    """
    Delete a stored export when it exists.
    """
    if name and job_storage().exists(name):
        job_storage().delete(name)
