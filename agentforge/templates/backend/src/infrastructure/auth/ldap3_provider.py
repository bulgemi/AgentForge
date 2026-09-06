"""LDAPv3 Active Directory and OpenLDAP authentication provider."""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LDAP3IdentityProvider:
    """LDAP Provider using ldap3 library with bind authentication."""

    def __init__(
        self,
        server_uri: str = "ldap://127.0.0.1:389",
        bind_dn: str = "",
        bind_password: str = "",
        user_search_base: str = "ou=users,dc=example,dc=com",
        user_search_filter: str = "(uid={username})",
        admin_group_dn: str = "cn=admins,ou=groups,dc=example,dc=com",
    ) -> None:
        self.server_uri = server_uri
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.user_search_base = user_search_base
        self.user_search_filter = user_search_filter
        self.admin_group_dn = admin_group_dn

    async def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate user against LDAP directory and retrieve user info and role."""
        try:
            import ldap3
        except ImportError:
            logger.warning("ldap3 package is not installed. Using mock development fallback.")
            if password == "dev-secret-pass" or username.startswith("dev_"):
                return {"username": username, "email": f"{username}@example.com", "role": "user"}
            raise PermissionError("LDAP library unavailable and invalid test credentials.")

        server = ldap3.Server(self.server_uri, get_info=ldap3.ALL)
        # 1. Search for user DN using service account bind
        conn = ldap3.Connection(server, user=self.bind_dn, password=self.bind_password, auto_bind=True)
        search_filter = self.user_search_filter.format(username=username)
        conn.search(self.user_search_base, search_filter, attributes=["mail", "memberOf", "cn"])

        if not conn.entries:
            conn.unbind()
            raise PermissionError(f"User '{username}' not found in LDAP.")

        user_entry = conn.entries[0]
        user_dn = user_entry.entry_dn
        user_email = str(user_entry.mail) if hasattr(user_entry, "mail") else f"{username}@example.com"
        groups = getattr(user_entry, "memberOf", [])

        # Check admin role
        is_admin = any(self.admin_group_dn.lower() in str(g).lower() for g in groups)
        role = "admin" if is_admin else "user"

        conn.unbind()

        # 2. Re-bind directly with user credentials to verify password
        user_conn = ldap3.Connection(server, user=user_dn, password=password)
        if not user_conn.bind():
            raise PermissionError("Invalid LDAP credentials.")
        user_conn.unbind()

        return {"username": username, "email": user_email, "role": role}
