from datetime import datetime
from os.path import basename

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now
from model_utils.models import TimeStampedModel

from ..const import PERM_CAN_ADMIN_CLAIMS, PERM_CAN_EDIT_CLAIMS_CATEGORY
from .managers import ClaimsManager
from .validators import invoice_file_path, invoice_file_validate


# Create your models here.
class ClaimsCategory(TimeStampedModel):
    class Meta:
        ordering = ("-created",)
        default_permissions = ()
        permissions = ((PERM_CAN_EDIT_CLAIMS_CATEGORY, "Can edit claims category"),)

    name = models.TextField(default="", unique=True)
    description = models.TextField(default="", blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Claims(TimeStampedModel):
    objects = ClaimsManager()

    class Meta:
        ordering = ("-created",)
        default_permissions = ()
        permissions = ((PERM_CAN_ADMIN_CLAIMS, "Can administrate claims"),)

    class StatusChoice(models.TextChoices):
        OPEN = ("OPEN", "Open")
        IN_PROGRESS = ("IN_PROGRESS", "In progress")
        REJECTED = ("REJECTED", "Rejected")
        APPROVED = ("APPROVED", "Approved")

    invoice_id = models.TextField(default="")
    invoice_date = models.DateField()
    category = models.ForeignKey(ClaimsCategory, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, default=None
    )
    invoice_file = models.FileField(
        upload_to=invoice_file_path,
        help_text="Max 5MB in file size",
        validators=(invoice_file_validate,),
    )
    status = models.CharField(
        choices=StatusChoice, default=StatusChoice.OPEN, max_length=100
    )

    def __str__(self) -> str:
        return self.invoice_id

    def save(self, *args, **kwargs):
        is_created = not self.pk
        super().save(*args, **kwargs)

        if is_created:
            self.init_create_logs()

    def init_create_logs(self):
        ClaimsLogs.objects.create(
            claim=self,
            remarks="",
            user=self.created_by,
            created=self.created,
            modified=self.created,
        )

    def approve(self, user_id, remarks: str, created: datetime | None = None):
        # skip rejected or approved claims
        if self.status in (self.StatusChoice.REJECTED, self.StatusChoice.APPROVED):
            raise ValidationError(
                f"Cannot process claim from {self.status} to APPROVED"
            )

        created_data = {}
        if created:
            created_data["created"] = created
            created_data["modified"] = created

        ClaimsLogs.objects.create(
            claim=self,
            remarks=remarks,
            user_id=user_id,
            action=ClaimsLogs.ActionChoice.APPROVE,
            **created_data,
        )

        if self.status != self.StatusChoice.IN_PROGRESS:
            self.status = self.StatusChoice.IN_PROGRESS
            self.save()

    def reject(self, user_id, remarks: str, created: datetime | None = None):
        # skip rejected or approved claims
        if self.status in (self.StatusChoice.REJECTED, self.StatusChoice.APPROVED):
            raise ValidationError(
                f"Cannot process claim from {self.status} to REJECTED"
            )

        created_data = {}
        if created:
            created_data["created"] = created
            created_data["modified"] = created

        ClaimsLogs.objects.create(
            claim=self,
            remarks=remarks,
            user_id=user_id,
            action=ClaimsLogs.ActionChoice.REJECT,
            **created_data,
        )

        self.status = self.StatusChoice.REJECTED
        self.save()

    def finalize(self, user_id, remarks: str, created: datetime | None = None):
        # skip open, rejected or approved claims
        if self.status in (
            self.StatusChoice.OPEN,
            self.StatusChoice.REJECTED,
            self.StatusChoice.APPROVED,
        ):
            raise ValidationError(
                f"Cannot process claim from {self.status} to FINALIZED"
            )

        created_data = {}
        if created:
            created_data["created"] = created
            created_data["modified"] = created

        ClaimsLogs.objects.create(
            claim=self,
            remarks=remarks,
            user_id=user_id,
            action=ClaimsLogs.ActionChoice.FINALIZE,
            **created_data,
        )

        self.status = self.StatusChoice.APPROVED
        self.save()

    def duplicate(self):
        self.pk = None
        self.invoice_id += " (copy)"

        # dupe invoice file
        self.invoice_file = ContentFile(
            self.invoice_file.read(), basename(self.invoice_file.name)
        )

        # setting back defaults
        for field_name in (
            "created",
            "modified",
            "status",
        ):
            default_value = Claims._meta.get_field(field_name).get_default()
            setattr(self, field_name, default_value)

        self.save()
        return self


class ClaimsLogs(TimeStampedModel):
    class Meta:
        ordering = ("-created",)
        default_permissions = ()
        indexes = [
            models.Index(fields=("claim",)),
        ]

    class ActionChoice(models.TextChoices):
        CREATE = ("CREATE", "Create")
        APPROVE = ("APPROVE", "Approve")
        REJECT = ("REJECT", "Reject")
        FINALIZE = ("FINALIZE", "Finalize")

    claim = models.ForeignKey(Claims, on_delete=models.CASCADE, related_name="logs")
    remarks = models.TextField(default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, default=None
    )
    action = models.CharField(
        choices=ActionChoice, default=ActionChoice.CREATE, max_length=100
    )
