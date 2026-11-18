# Module outputs (episode 7). Public IDs: they go in the browser bundle and the service env.

output "user_pool_id" { value = aws_cognito_user_pool.this.id }        # COGNITO_USER_POOL_ID, NEXT_PUBLIC_USER_POOL_ID
output "web_client_id" { value = aws_cognito_user_pool_client.web.id } # COGNITO_CLIENT_ID, NEXT_PUBLIC_USER_POOL_CLIENT_ID
