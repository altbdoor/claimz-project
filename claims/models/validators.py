from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.fields.files import FieldFile


def invoice_file_path(instance, filename: str) -> str:
    today = date.today()
    date_path = f"{today.year}/{today.month}/{today.day}"
    return f"claims/{instance.created_by.id}/{date_path}/{filename}"


def invoice_file_validate(value: FieldFile):
    if value.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError("File size is over 5MB")
