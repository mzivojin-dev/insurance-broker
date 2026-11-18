# Module: cognito (episode 7). Sign-in for the client chat widget.
#
# The ID token carries custom:client_id, and client_service/auth.py scopes every tool call by it.
# Two settings make that safe:
#   - only admins create users, so nobody signs up without a client attached
#   - the web app client can read custom:client_id but not write it, so a user can't move
#     themselves to another client with UpdateUserAttributes
#
# Users:
#   aws cognito-idp admin-create-user --user-pool-id <id> --username dana@example.com \
#     --user-attributes Name=email,Value=dana@example.com Name=email_verified,Value=true \
#                       Name=custom:client_id,Value=C-1042

resource "aws_cognito_user_pool" "this" {
  name                     = var.name
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = var.deletion_protection

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  # Custom attributes can't be changed or removed after the pool exists.
  schema {
    name                     = "client_id"
    attribute_data_type      = "String"
    mutable                  = true # admins set it; the app client below can't write it
    developer_only_attribute = false
    string_attribute_constraints {
      min_length = 1
      max_length = 32
    }
  }
}

resource "aws_cognito_user_pool_client" "web" {
  name                          = "${var.name}-web"
  user_pool_id                  = aws_cognito_user_pool.this.id
  generate_secret               = false # a browser can't keep a secret
  explicit_auth_flows           = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors = "ENABLED"

  read_attributes = ["email", "email_verified", "custom:client_id"]
  # Must be explicit: left empty, Cognito lets the app client write every attribute.
  write_attributes = ["email"]

  id_token_validity      = 60 # minutes
  access_token_validity  = 60
  refresh_token_validity = 7 # days
  token_validity_units {
    id_token      = "minutes"
    access_token  = "minutes"
    refresh_token = "days"
  }
}
