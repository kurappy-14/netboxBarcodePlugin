"""Permission helpers using NetBox Object Permissions."""


def has_object_perm(user, perm, obj):
    """Check a NetBox/Django object permission.

    NetBox's ObjectPermission backend participates in ``user.has_perm`` with
    an object argument. Superusers are allowed by NetBox convention.
    """

    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return bool(user.has_perm(perm, obj))


def can_view_cable(user, cable):
    """Return True when *user* may view the Cable details."""

    return has_object_perm(user, "dcim.view_cable", cable)


def can_change_cable(user, cable):
    """Return True when *user* may update the Cable."""

    return has_object_perm(user, "dcim.change_cable", cable)
