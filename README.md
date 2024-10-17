# ITSlearning Scraper

## Description

Itslearning is a school management platform that does not integrate with emails or slack. In order to stay up to date, you have to check the platform manually. This scraper will check the platform for new messages and notifications and send them via email.

## Local Development and Testing

### Prerequisites

- Docker and Docker Compose installed on your machine
- AWS CLI configured (for pushing to ECR)

### Local Setup

1. Clone the repository:
   ```
   git clone [your-repo-url]
   cd [your-repo-directory]
   ```

2. Create a `.env` file in the root directory with your configuration:
   ```
   ITSLEARNING_USERNAME=your_username
   ITSLEARNING_PASSWORD=your_password
   SMTP_SERVER=your_smtp_server
   SMTP_PORT=your_smtp_port
   SMTP_USERNAME=your_smtp_username
   SMTP_PASSWORD=your_smtp_password
   EMAIL_FROM=your_email
   EMAIL_TO=recipient_email1,recipient_email2
   LOG_LEVEL=DEBUG  # Set to INFO, WARNING, or ERROR for production
   ```

3. Build and run the containers locally:
   ```
   docker-compose up --build
   ```

4. For development mode (to keep the container running without executing the script):
   ```
   docker-compose run -e RUN_MODE=development -it scraper bash
   ```
   This will start the scraper container in the background without running the main script.

5. To run the script manually in development mode:
   ```
   docker-compose exec scraper python lambda_function.py
   ```

## Production Deployment

### Building and Pushing to ECR

1. Build the Docker image:
   ```
   docker buildx build --platform linux/amd64 -t itslearning-scraper .
   ```

2. Authenticate Docker to your ECR registry:
   ```
   aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper
   ```

3. Tag your image:
   ```
   docker tag itslearning-scraper:latest 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper:latest
   ```

4. Push the image to ECR:
   ```
   docker push 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper:latest
   ```

### Deploying to AWS

1. Ensure your AWS CLI is configured with the correct credentials and region.

2. Update the `terraform.tfvars` file with your production values.

3. Apply the Terraform configuration:
   ```
   terraform init
   terraform apply
   ```

4. This will set up the ECS task, EventBridge rule, and other necessary AWS resources.

## Configuration

- Environment variables can be set in the `.env` file for local development and in the AWS ECS task definition for production.
- Logging level can be adjusted by setting the `LOG_LEVEL` environment variable.

## Troubleshooting

- Check the CloudWatch logs in AWS for any errors in production.
- For local debugging, set `LOG_LEVEL=DEBUG` in your `.env` file.
- If you encounter connection issues with Selenium, ensure the Selenium container is fully started before the scraper attempts to connect.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.