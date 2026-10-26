"""Señales del módulo de cuentas."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.usuarios.models import User


@receiver(post_save, sender=User)
def sync_staff_flag(sender, instance: User, **kwargs):
    """Mantiene ``is_staff`` coherente con los roles administrativos.

    Un superusuario siempre necesita acceso al admin; el resto de roles lo
    recibe solo si se marca explícitamente.
    """
    if instance.is_superuser and not instance.is_staff:
        User.objects.filter(pk=instance.pk).update(is_staff=True)
