import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from users.models import AuditLog

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates a new user account'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the new user')

        parser.add_argument(
            '--email',
            type=str,
            help='Email address for the user'
        )

        parser.add_argument(
            '--full-name',
            type=str,
            help='Full name of the user'
        )

        parser.add_argument(
            '--admin',
            action='store_true',
            help='Make the user an admin'
        )

        parser.add_argument(
            '--password',
            type=str,
            help='Password for the user (if not provided, will prompt)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options.get('email')
        full_name = options.get('full_name')
        is_admin = options.get('admin', False)
        password = options.get('password')

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists')

        # Prompt for password if not provided
        if not password:
            password = getpass.getpass('Enter password: ')
            password_confirm = getpass.getpass('Confirm password: ')

            if password != password_confirm:
                raise CommandError('Passwords do not match')

        try:
            with transaction.atomic():
                # Create the user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    full_name=full_name,
                    is_admin=is_admin,
                    is_staff=is_admin
                )

                # Create audit log
                AuditLog.objects.create(
                    user=None,  # System action
                    action='User created via management command',
                    action_details={
                        'user_id': user.id,
                        'username': user.username,
                        'is_admin': is_admin
                    }
                )

                self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))

                if is_admin:
                    self.stdout.write(self.style.SUCCESS('User is an admin'))

        except Exception as e:
            raise CommandError(f'Error creating user: {str(e)}')