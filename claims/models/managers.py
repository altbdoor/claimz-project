from django.db import models


class ClaimsManager(models.Manager):
    def get_queryset(self) -> models.QuerySet:
        # always get the category
        return super().get_queryset().select_related("category")
