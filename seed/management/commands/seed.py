import logging
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from claims.models import Claims, ClaimsCategory, ClaimsLogs

Faker.seed(12345)
fake = Faker()

User = get_user_model()

base_categories = (
    "Medical",
    "Grocery",
    "Travel",
)

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    # def add_arguments(self, parser):
    #     # Positional arguments
    #     parser.add_argument("poll_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        if not User.objects.filter(username="admin").exists():
            logging.info("admin does not exist, creating...")
            User.objects.create_superuser(username="admin", password="admin")

        if not User.objects.filter(username="staff").exists():
            logging.info("staff does not exist, creating...")
            staff = User.objects.create(username="staff")
            staff.set_password("staff")
            staff.save()

        ClaimsCategory.objects.bulk_create(
            [ClaimsCategory(name=cat) for cat in base_categories], ignore_conflicts=True
        )
        logging.info("creating categories")

        Claims.objects.all().delete()
        logging.info("dropped all claims")

        User.objects.all().exclude(
            username__in=(
                "admin",
                "staff",
            )
        ).delete()
        logging.info("dropped all users")

        try:
            category_pks = ClaimsCategory.objects.values_list("pk", flat=True)
            admin_pk = User.objects.get(username="admin").pk

            with transaction.atomic():
                for _ in range(50):
                    username = fake.unique.user_name()
                    user, user_created = User.objects.get_or_create(username=username)
                    if user_created:
                        user.set_password("password")
                        user.save()

                    claim_count = self.create_claims_for_user_pk(
                        admin_pk, user.pk, category_pks
                    )
                    logging.info(f"created {claim_count} for {username}")

        except Exception as ex:
            logging.error(ex)

    def create_claims_for_user_pk(self, admin_pk, user_pk, category_pks: list):
        claims_dataset = []

        for _ in range(fake.pyint(max_value=20)):
            created: datetime = fake.date_time_between(
                start_date="-90d", tzinfo=timezone.utc
            )

            claims_dataset.append(
                Claims(
                    invoice_id=fake.ssn(),
                    invoice_date=created.date(),
                    category_id=fake.random_choices(elements=category_pks, length=1)[0],
                    amount=fake.pydecimal(
                        right_digits=2, min_value=1.0, max_value=20_000.0
                    ),
                    description=fake.paragraph(nb_sentences=5),
                    created_by_id=user_pk,
                    invoice_file="claims/sample.pdf",
                    created=created,
                    modified=created,
                )
            )

        created_claims = Claims.objects.bulk_create(claims_dataset)
        updated_claims = []

        for claim in created_claims:
            claim.init_create_logs()

            if fake.pybool(truth_probability=30):
                # take action for this claim

                if fake.pybool():
                    # reject the claim
                    claim.reject(admin_pk, "", claim.created + timedelta(hours=2))
                    claim.modified = claim.created + timedelta(hours=2)
                else:
                    # approve the claim
                    claim.approve(admin_pk, "", claim.created + timedelta(hours=2))
                    claim.modified = claim.created + timedelta(hours=2)

                    if fake.pybool(truth_probability=10):
                        claim.reject(admin_pk, "", claim.created + timedelta(hours=4))
                        claim.modified = claim.created + timedelta(hours=4)
                    elif fake.pybool(truth_probability=50):
                        claim.finalize(admin_pk, "", claim.created + timedelta(hours=4))
                        claim.modified = claim.created + timedelta(hours=4)

                updated_claims.append(claim)

        Claims.objects.bulk_update(updated_claims, ["modified"])
        return len(claims_dataset)
