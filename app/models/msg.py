
from pydantic import BaseModel


class DefaultMessage(BaseModel):
    request_id: str
    message: str
    note: str | None = None


class Message:
    token_not_found = "Token not found"
    user_is_not_updated = "User was not updated"
    token_revoked = "Token revoked"
    invalid_client_credentials = "Invalid client credentials"
    missing_or_invalid_client_credentials = "Missing or invalid client credentials"
    invalid_password_or_login = "Invalid password or login"
    input_login_and_password = "Input login and password"
    user_is_already_registered = "User is already registered"
    user_not_found = "User not found"
    client_mismath = "Client mismatch"
    redirect_uri_mismath = "Redirect URI mismatch"
    invalid_redirect_uri = "Invalid redirect URI"
    code_client_mismath = "Code client mismatch"
    user_is_updated = "User was updated"
    user_is_deleted = "User deleted"
    token_invalid = "Invalid token"
    refresh_token_invalid = "Invalid refresh token"
    refresh_token_invalid_or_missing = "Invalid or missing refresh token"
    token_invalid_or_missing = "Missing or invalid token"
    unsupported_grant_type = "Unsupported grant_type"
    token_invalid_payload = "Invalid token payload"
    invalid_or_expired_code = "Invalid or expired code"
    internal_error = "Internal error"
    invalid_or_missing_code_or_redirect_uri = "Invalid or missing code/redirect_uri"
    invalid_client_secret = "Invalid client secret"
    invalid_client = "Invalid client"
    invalid_ot_missing_form_parameters = "Invalid or missing form parameters"
    only_authorization_code_flow_is_supported = "Only authorization_code flow is supported"
