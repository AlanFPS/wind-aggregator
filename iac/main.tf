###############################################################################
# Wind-Damage Aggregator – Terraform stack (AWS)
###############################################################################

# ---- provider --------------------------------------------------------------
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_profile" { default = "wind-demo" }
variable "aws_region"  { default = "us-east-1" }

provider "aws" {
  profile = var.aws_profile
  region  = var.aws_region
}

provider "archive" {}

# ---- package Lambda --------------------------------------------------------
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda.zip"
  excludes    = ["__pycache__"]
}

# ---- IAM role --------------------------------------------------------------
resource "aws_iam_role" "lambda_exec" {
  name               = "wind_lambda_role"
  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [{
      Action: "sts:AssumeRole",
      Effect: "Allow",
      Principal: { Service: "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_exec.id
  policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      { Action: [
          "rekognition:DetectLabels"
        ],
        Effect: "Allow",
        Resource: "*" },
      { Action: [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Effect: "Allow",
        Resource: "*" }
    ]
  })
}

# ---- Lambda function -------------------------------------------------------
resource "aws_lambda_function" "agg" {
  function_name = "wind-aggregator"
  role          = aws_iam_role.lambda_exec.arn
  runtime       = "python3.11"
  handler       = "wind_agg.handler.lambda_handler"
  filename      = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  timeout      = 60
  memory_size  = 1024

  environment {
    variables = {
      LOG_LEVEL = "INFO"
    }
  }

  depends_on = [aws_iam_role_policy.lambda_policy]
}

# ---- API Gateway HTTP API --------------------------------------------------
resource "aws_apigatewayv2_api" "http" {
  name          = "wind-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id             = aws_apigatewayv2_api.http.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.agg.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_agg" {
  api_id    = aws_apigatewayv2_api.http.id
  route_key = "POST /aggregate"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "allow_api" {
  statement_id  = "AllowInvokeByAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.agg.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
}

output "invoke_url" {
  value = aws_apigatewayv2_api.http.api_endpoint
}