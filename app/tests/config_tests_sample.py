import uuid


class ConfigTestsSample:
    # Конфигурация тестового LDAP
    LDAP_CONTAINER_NAME = "test-ldap-server"
    LDAP_PORT = 389
    LDAP_BASE_DN = "dc=example,dc=org"
    LDAP_ADMIN_DN = "cn=admin,dc=example,dc=org"
    LDAP_ADMIN_PASSWORD = "admin_password"
    LDAP_DOMAIN = "example.org"

    # Конфигурация тестового GitLab (OIDC Provider)
    GITLAB_CONTAINER_NAME = "test-gitlab-server"
    GITLAB_HOST = "localhost"
    GITLAB_HTTP_PORT = 8929
    GITLAB_HTTPS_PORT = 443  # не используется
    GITLAB_ROOT_PASSWORD = f"test-{uuid.uuid4()}"
    GITLAB_OAUTH_APP_NAME = "TestOIDCClient"
    GITLAB_REDIRECT_URI = "http://localhost:8000/callback"
    GITLAB_CONTAINER_TIMEOUT = 600
