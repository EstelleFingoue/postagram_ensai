# Aidez-vous du TP 2


variable "git_repo" {
  type    = string
  default = "https://github.com/EstelleFingoue/postagram_ensai.git" # <- a remplacer par l'url de votre dépôt git
}

# Nom de l'instance profile IAM pour les EC2 (LabInstanceProfile pour AWS Academy ; sinon vérifier IAM → Instance profiles)
variable "iam_instance_profile_name" {
  type    = string
  default = "LabInstanceProfile"
}

########################################
# Launch Template
########################################

resource "aws_launch_template" "ubuntu_template" {
  name_prefix   = "postagram-"
  image_id      = "ami-0ecb62995f68bb549"
  instance_type = "t3.micro"
  key_name      = "vockey"
  iam_instance_profile {
    name = var.iam_instance_profile_name # <- NE PAS MODIFIER (valeur via variable)
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    git_repo     = var.git_repo
    dynamo_table = aws_dynamodb_table.basic-dynamodb-table.name
    bucket       = aws_s3_bucket.bucket.bucket
  }))

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  block_device_mappings {
    device_name = "/dev/sda1"

    ebs {
      volume_size = 8
      volume_type = "gp3"
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "postagram-instance"
    }
  }
  tags = {
    Name = "TP noté"
  }
}
# Notes: AMI fournie (ami-0ecb62995f68bb549), t3.micro, vockey, LabRole ; user_data avec templatefile pour clone du repo, BUCKET et DYNAMO_TABLE ; webservice sur port 8080 (sujet).

########################################
# Auto Scaling Group
########################################
resource "aws_autoscaling_group" "web_asg" {
  desired_capacity    = 1
  max_size            = 4
  min_size            = 1
  vpc_zone_identifier = data.aws_subnets.default.ids
  health_check_type   = "ELB"
  target_group_arns   = [aws_lb_target_group.web_tg.arn]

  launch_template {
    id      = aws_launch_template.ubuntu_template.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "web-asg-instance"
    propagate_at_launch = true
  }
}
# Notes: min 1, max 4, desired 1 (sujet) ; health_check_type ELB pour health-check sur le port 8080 du TG ; target_group_arns pour attacher les instances au TG.

########################################
# Load Balancer (ALB)
########################################
resource "aws_lb" "web_alb" {
  name               = "web-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_sg.id]
  subnets            = data.aws_subnets.default.ids

  tags = {
    Name = "web-alb"
  }
}
# Notes: ALB application pour répartir le trafic HTTP vers le Target Group (port 8080).

########################################
# Target Group (pour le Load Balancer)
########################################
resource "aws_lb_target_group" "web_tg" {
  name     = "web-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id

  health_check {
    path                = "/posts"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  tags = {
    Name = "web-tg"
  }
}
# Notes: port 8080 et protocol HTTP pour correspondre au webservice (app.py uvicorn port 8080). health_check sur /posts car l'app n'a pas de route GET / (sinon 404 → unhealthy → 502).

########################################
# Listener pour le Load Balancer
########################################
resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.web_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web_tg.arn
  }
}
# Notes: écoute sur le port 80 et forward vers le Target Group (webservice sur 8080).

########################################
# Outputs
########################################
output "load_balancer_dns_name" {
  description = "Nom DNS du load balancer"
  value       = aws_lb.web_alb.dns_name
}
# Notes: URL à utiliser pour les tests et pour webapp (axios.baseURL) après déploiement.

