# ITSlearning scraper

## Description

Itslearning is a school management platform that does not integrate with emails or slack. In order to stay up to date, you have to check the platform manually. This scraper will check the platform for new messages and send them to a slack channel.

## Build the image

docker build -t itslearning-scraper .

## Authenticate Docker to your ECR registry

aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper

## Tag your image

docker tag itslearning-scraper:latest 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper:latest

## Push the image to ECR

docker push 873519902872.dkr.ecr.eu-central-1.amazonaws.com/itslearning-scraper:latest