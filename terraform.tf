# Configure the AWS provider
provider "aws" {
  region = "eu-central-1"  # Replace with your desired region
}

# Lambda function
resource "aws_lambda_function" "itslearning_scraper" {
  filename         = "./lambda_package/function.zip"
  function_name    = "ItslearningScraper"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  timeout          = 300
  memory_size      = 2048

  environment {
    variables = {
      PARAMETER_PREFIX = "/itslearning_scraper"
    }
  }

  layers = ["arn:aws:lambda:eu-central-1:764866452798:layer:chrome-selenium:34"]
}

# IAM role for the Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "itslearning_scraper_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# CloudWatch Log Group for Lambda function
resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${aws_lambda_function.itslearning_scraper.function_name}"
  retention_in_days = 14
}

# IAM policy for CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# EventBridge (CloudWatch Events) rule for scheduling
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "itslearning_scraper_schedule"
  description         = "Schedule for Itslearning Scraper Lambda Function"
  schedule_expression = "cron(0 12 * * ? *)"
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "ItslearningScraperTarget"
  arn       = aws_lambda_function.itslearning_scraper.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.itslearning_scraper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}

# Output the Lambda function ARN
output "itslearning_scraper_function_arn" {
  description = "Itslearning Scraper Lambda Function ARN"
  value       = aws_lambda_function.itslearning_scraper.arn
}