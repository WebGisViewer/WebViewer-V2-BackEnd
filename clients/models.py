# clients/models.py
from django.db import models
from django.utils import timezone
from projects.models import Project  # Import the Project model


class Client(models.Model):
    """Client organization that can access the WebGIS platform."""

    name = models.CharField(max_length=255, unique=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clients_wiroi_online'
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


# clients/models.py (additional)
class ClientProject(models.Model):
    """Relationship between Clients and Projects with access control."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='client_projects')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='client_projects')
    unique_link = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'client_projects_wiroi_online'
        verbose_name = 'Client Project'
        verbose_name_plural = 'Client Projects'
        unique_together = ('client', 'project')

    def __str__(self):
        return f"{self.client.name} - {self.project.name}"

    def save(self, *args, **kwargs):
        # Generate a unique hash code if not provided
        if not self.unique_link and not self.pk:
            import uuid
            import hashlib

            # Generate a unique hash
            unique_id = uuid.uuid4().hex
            hash_input = f"{self.client_id}-{self.project_id}-{unique_id}"
            self.unique_link = hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        super().save(*args, **kwargs)