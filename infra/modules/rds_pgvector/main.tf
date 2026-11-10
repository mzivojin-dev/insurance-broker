resource "aws_db_instance" "this" {
  identifier                  = "ai4all-${var.env}"
  engine                      = "postgres"
  engine_version              = "18" # major only: AWS picks the newest 18.x; pgvector is built in
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  db_name                     = "ai4all"
  username                    = "ai4all_admin"
  manage_master_user_password = true # password lives in Secrets Manager
  db_subnet_group_name        = var.db_subnet_group
  vpc_security_group_ids      = [aws_security_group.db.id]
  storage_encrypted           = true
  backup_retention_period     = var.ephemeral ? 0 : 7 # backups die with a daily-destroyed DB anyway
  skip_final_snapshot         = var.ephemeral         # prod is torn down daily; data comes back from the seed job
  deletion_protection         = !var.ephemeral
}

resource "aws_security_group" "db" {
  name   = "ai4all-${var.env}-db"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids # only the ECS tasks
  }
}