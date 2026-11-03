from .models import AuditLog


def log_action(user, aksi, obj, changes=None, ringkasan=""):
    """Catat aktivitas penting ke tabel audit_logs."""
    if obj is None:
        return None
    if not ringkasan:
        ringkasan = str(obj)[:255]
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        aksi=aksi,
        model_name=obj.__class__.__name__,
        object_id=str(obj.pk),
        ringkasan=ringkasan,
        changes=changes or {},
    )
