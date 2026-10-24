from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand,CommandError
from django.core.management import call_command
class Command(BaseCommand):
    help='Create an administrator interactively through Django; never grants access to the first browser visitor.'
    def handle(self,*args,**options):
        if get_user_model().objects.filter(is_superuser=True,is_active=True).exists(): raise CommandError('An active administrator already exists. Use controlled account administration.')
        call_command('createsuperuser')
