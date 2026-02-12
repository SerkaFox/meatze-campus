# shortshare/management/commands/shortshare_cleanup.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from panel.shortshare.models import ShortFile

class Command(BaseCommand):
    help = "Delete expired shortshare files"

    def handle(self, *args, **kwargs):
        qs = ShortFile.objects.filter(expires_at__lte=timezone.now())
        n = qs.count()
        for obj in qs.iterator():
            try:
                obj.file.delete(save=False)
            finally:
                obj.delete()
        self.stdout.write(f"Deleted {n} expired files")