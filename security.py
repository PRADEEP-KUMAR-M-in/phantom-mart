import hashlib
import hmac
import os

# roles that are allowed to add / edit / delete records
EDIT_ROLES = ("Admin", "Manager")

# roles that can open the sales report page
REPORT_ROLES = ("Admin", "Manager")

# settings, backup and restore
SYSTEM_ROLES = ("Admin",)

ITERATIONS = 120000

def can_edit(current_user):
    return current_user["role"] in EDIT_ROLES

def can_manage_system(current_user):
    return current_user["role"] in SYSTEM_ROLES

def can_view_reports(current_user):
    return current_user["role"] in REPORT_ROLES

# passwords are stored as  pbkdf2$iterations$salt$hash
def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"

def is_hashed(value):
    return str(value).startswith("pbkdf2$")

def verify_password(password, stored):
    if not is_hashed(stored):
        return False
    try:
        _, iterations, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
    except ValueError:
        return False
    return hmac.compare_digest(check.hex(), digest)
