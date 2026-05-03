
from pydantic import BaseModel


class DefaultMessage(BaseModel):
    request_id: str
    message: str
    note: str | None = None


class Message:
    user_blocking_status_changed = "User blocking status successfully changed"
    user_blocked = "User blocked"
    user_not_blocked = "User not blocked"
    user_is_not_registered = "User is not registered"
    user_is_not_updated = "User was not updated"
    wrong_password = "Wrong password"
    permission_denied = "Access denied"
    can_not_block_admin = "Cannot block administrator"
    can_not_verify_admin = "Cannot verify administrator"
    can_not_unverify_admin = "Cannot unverify administrator"
    user_is_not_blocked = "User is not blocked"
    user_is_not_verified = "User is not verified"
    user_is_verified = "User is verified"
    user_is_blocked = "User is blocked"
    only_admin_have_access = "Access is allowed only for administrator"
    wrong_email = "Invalid email"
    link_invalid = "Link is not valid, please repeat registration process"
    email_already_confirmed = "Email is already confirmed"
    user_image_is_not_deleted = "User image not deleted"
    user_image_is_not_updated = "User image not updated"

    # Token messages
    token_not_found = "Token not found"
    token_expired = "Token has expired"

    # System messages
    incorrect_json_format = "Invalid JSON format"
    unknown_error = "Unknown error"
    evil_attempt_to_change_email = "Unauthorized attempt to change email"
    code_has_been_sent = "An email with a code has been sent to your email address. You can resubmit your request in 1 minute"
    confirm_email_has_been_sent = "A confirmation email has been sent to your email address. You can resubmit your request in 5 minutes"
    authorization_successful = "Authorization successful"
    exit_was_successful = "The exit was successful"
    email_successfully_confirmed = "Email successfully confirmed!"


    # SSO msg
    community_limit = "Community limit: no more than 2 clients"
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
