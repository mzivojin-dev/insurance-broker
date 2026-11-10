output "address" { value = aws_db_instance.this.address }

# JSON with username and password; ECS reads the keys with "<arn>:username::" and "<arn>:password::"
output "master_secret_arn" { value = aws_db_instance.this.master_user_secret[0].secret_arn }
