# projects/management/commands/generate_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from clients.models import Client, ClientProject
from projects.models import Project
import random
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Generates test data for the WebGIS Viewer V2 application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clients',
            type=int,
            default=5,
            help='Number of clients to create'
        )

        parser.add_argument(
            '--users',
            type=int,
            default=20,
            help='Number of users to create'
        )

        parser.add_argument(
            '--projects',
            type=int,
            default=15,
            help='Number of projects to create'
        )

        parser.add_argument(
            '--client-projects',
            type=int,
            default=30,
            help='Number of client-project assignments to create'
        )

    def handle(self, *args, **options):
        self.stdout.write('Generating test data...')

        # Create admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                is_admin=True,
                full_name='Admin User'
            )
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write('Admin user already exists')

        # Create clients
        clients = []
        for i in range(options['clients']):
            client = Client.objects.create(
                name=f'Test Client {i + 1}',
                contact_email=f'contact{i + 1}@testclient.com',
                contact_phone=f'555-{i + 1:03d}-{random.randint(1000, 9999)}',
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            clients.append(client)
            self.stdout.write(f'Created client: {client.name}')

        # Create regular users
        users = []
        for i in range(options['users']):
            is_admin = random.random() < 0.2  # 20% chance of being admin
            client = None if is_admin else random.choice(clients)

            user = User.objects.create_user(
                username=f'user{i + 1}',
                email=f'user{i + 1}@example.com',
                password=f'password{i + 1}',
                full_name=f'Test User {i + 1}',
                is_admin=is_admin,
                client=client
            )
            users.append(user)
            self.stdout.write(
                f'Created user: {user.username} (admin: {is_admin}, client: {client.name if client else "None"})')

        # Create projects
        projects = []
        for i in range(options['projects']):
            creator = random.choice([admin_user] + [u for u in users if u.is_admin])
            is_public = random.random() < 0.3  # 30% chance of being public

            project = Project.objects.create(
                name=f'Test Project {i + 1}',
                description=f'Description for test project {i + 1}',
                is_public=is_public,
                is_active=random.choice([True, True, True, False]),  # 75% active
                default_center_lat=random.uniform(25, 45),
                default_center_lng=random.uniform(-125, -75),
                default_zoom_level=random.randint(5, 12),
                max_zoom=random.randint(14, 18),
                min_zoom=random.randint(1, 4),
                map_controls={
                    'showZoomControl': random.choice([True, False]),
                    'showScaleControl': random.choice([True, False]),
                    'showLayerControl': random.choice([True, False])
                },
                map_options={
                    'enableClustering': random.choice([True, False]),
                    'clusterRadius': random.randint(50, 100),
                    'maxClusterRadius': random.randint(150, 300)
                },
                created_by_user=creator
            )
            projects.append(project)
            self.stdout.write(f'Created project: {project.name} (public: {is_public}, creator: {creator.username})')

        # Assign projects to clients
        for i in range(options['client_projects']):
            client = random.choice(clients)
            project = random.choice(projects)

            # Check if assignment already exists
            if ClientProject.objects.filter(client=client, project=project).exists():
                continue

            # Random expiration date (25% chance of having one)
            expires_at = None
            if random.random() < 0.25:
                days_in_future = random.randint(30, 365)
                expires_at = timezone.now() + timedelta(days=days_in_future)

            # Random last accessed date (60% chance of having one)
            last_accessed = None
            if random.random() < 0.6:
                days_in_past = random.randint(1, 30)
                last_accessed = timezone.now() - timedelta(days=days_in_past)

            client_project = ClientProject.objects.create(
                client=client,
                project=project,
                unique_link=f'link-{client.id}-{project.id}-{random.randint(1000, 9999)}',
                is_active=random.choice([True, True, True, False]),  # 75% active
                expires_at=expires_at,
                last_accessed=last_accessed
            )
            self.stdout.write(f'Assigned project {project.name} to client {client.name}')

        self.stdout.write(self.style.SUCCESS('Test data generation complete!'))

        # Summary
        self.stdout.write('\nSummary:')
        self.stdout.write(f'- Clients: {len(clients)}')
        self.stdout.write(f'- Users: {len(users) + 1} (including admin)')
        self.stdout.write(f'- Projects: {len(projects)}')
        self.stdout.write(f'- Client-Project Assignments: {ClientProject.objects.count()}')