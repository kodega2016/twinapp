# Week-02

<!--toc:start-->
- [Week-02](#week-02)
  - [Create Project Directories](#create-project-directories)
  - [Initialize Frontend Project](#initialize-frontend-project)
  - [Terraform Resource Provisioning](#terraform-resource-provisioning)
    - [Prerequisites](#prerequisites)
    - [1. Build Lambda deployment artifact](#1-build-lambda-deployment-artifact)
    - [2. Initialize Terraform](#2-initialize-terraform)
    - [3. Review variables](#3-review-variables)
    - [4. Plan and apply](#4-plan-and-apply)
    - [5. Get important outputs](#5-get-important-outputs)
    - [6. Set Lambda secret env vars after provisioning](#6-set-lambda-secret-env-vars-after-provisioning)
    - [7. Upload frontend build to provisioned S3 bucket](#7-upload-frontend-build-to-provisioned-s3-bucket)
    - [8. (Optional) One-command deployment script](#8-optional-one-command-deployment-script)
  - [Lets deploy the application to AWS](#lets-deploy-the-application-to-aws)
    - [Backend](#backend)
      - [Deployment to Lambda](#deployment-to-lambda)
      - [Create S3 Buckets](#create-s3-buckets)
      - [Lets expose the Lambda function with API Gateway](#lets-expose-the-lambda-function-with-api-gateway)
    - [Frontend](#frontend)
      - [Lets setup the CloudFront Distribution For Frontend](#lets-setup-the-cloudfront-distribution-for-frontend)
  - [Using AWS Bedrock for AI Models](#using-aws-bedrock-for-ai-models)
<!--toc:end-->

In this week, we are going to explore AI for building a chat AI assistant.
We will use a Next.js application for the frontend and FastAPI for the backend.

## Create Project Directories

```bash
mkdir twin
cd twin
mkdir backend
mkdir memory
```

## Initialize Frontend Project

Lets create a Next.js application with App Router support.

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir
```

We then start the backend project.

```bash
cd backend
uv init --bare
uv python pin 3.12
uv add -r requirements.txt
uv run uvicorn server:app --reload
```

After that, we can run the frontend server with the following command.

```bash
cd frontend
npm run dev
```

## Terraform Resource Provisioning

You can provision AWS resources (S3, Lambda, API Gateway, IAM, CloudFront)
from the Terraform files in `terraform/`.

### Prerequisites

- Terraform installed (`>= 1.0`)
- AWS CLI configured (`aws configure`)
- Docker running (required to build `backend/lambda-deployment.zip`)

### 1. Build Lambda deployment artifact

Terraform expects this file to exist: `backend/lambda-deployment.zip`.

```bash
cd backend
uv run deploy.py
cd ..
```

### 2. Initialize Terraform

```bash
cd terraform
terraform init
```

### 3. Review variables

Update `terraform/terraform.tfvars` as needed:

```hcl
environment  = "dev"
project_name = "twin-app"
```

Optional variables you can pass via CLI:

- `bedrock_model_id`
- `lamda_timeout`
- `api_throttle_burst_limit`
- `api_throttle_rate_limit`
- `use_custom_domain`
- `root_domain`

### 4. Plan and apply

```bash
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

For non-interactive apply:

```bash
terraform apply -var-file=terraform.tfvars -auto-approve
```

### 5. Get important outputs

```bash
terraform output api_gateway_url
terraform output cloudfront_url
terraform output s3_frontend_bucket
terraform output s3_memory_bucket
```

### 6. Set Lambda secret env vars after provisioning

`OPENAI_API_KEY` is intentionally not managed in Terraform state, so set it
directly on the function after apply:

```bash
LAMBDA_NAME=$(terraform output -raw lambda_function_name)
aws lambda update-function-configuration \
	--function-name "$LAMBDA_NAME" \
	--environment "Variables={OPENAI_API_KEY=YOUR_OPENAI_API_KEY}"
```

If you already have more environment variables in Lambda, include all of them in
the `Variables={...}` payload to avoid overwriting existing values.

### 7. Upload frontend build to provisioned S3 bucket

```bash
cd ../frontend
npm install
npm run build
FRONTEND_BUCKET=$(terraform -chdir=../terraform output -raw s3_frontend_bucket)
aws s3 sync out/ "s3://$FRONTEND_BUCKET/" --delete
```

### 8. (Optional) One-command deployment script

From repo root:

```bash
./scripts/deploy.sh dev twin-app
```

This script builds backend, applies Terraform, builds frontend, and uploads
frontend assets to S3.

## Lets deploy the application to AWS

So we are going to deploy our application to AWS with the following services:

### Backend

We are going to deploy our backend service in AWS Lambda, and the resources will
be stored in an S3 bucket. So first of all, we need to create the IAM role for the
AWS Lambda function to have access to S3 and CloudWatch so that it can interact
with S3 and CloudWatch logs.

#### Deployment to Lambda

So we created a Lambda function with name `twin-api` with `python:3.12` runtime
and the function handler `lambda_handler.handler` to handle incoming requests.
Then we uploaded `lambda-handler.zip`.

After that, we updated environment variables as well:

```bash
CORS_ORIGINS=*
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
S3_BUCKET=twin-memory
USE_S3=true
```

After updating the environment variables, we can test the function with the
following test event.

```json
{
	"version": "2.0",
	"routeKey": "GET /health",
	"rawPath": "/health",
	"headers": {
		"accept": "application/json",
		"content-type": "application/json",
		"user-agent": "test-invoke"
	},
	"requestContext": {
		"http": {
			"method": "GET",
			"path": "/health",
			"protocol": "HTTP/1.1",
			"sourceIp": "127.0.0.1",
			"userAgent": "test-invoke"
		},
		"routeKey": "GET /health",
		"stage": "$default"
	},
	"isBase64Encoded": false
}
```

#### Create S3 Buckets

We need to create an S3 bucket for storing memory and session chat data.
The bucket name must be globally unique and the region should be the same as
the AWS Lambda function.

name: `twin-memory-agentic-app`

After that, we need to attach S3 permission to the Lambda function execution role.

Go to Configuration:

- Click Permission
- Go to Execution role -> Add permission -> AmazonS3FullAccess

After bucket creation, update the Lambda environment variables with the new S3 bucket name.

#### Lets expose the Lambda function with API Gateway

Now we can create API Gateway to expose the Lambda function as an API.
First create an API in API Gateway named `twin-api-gateway`.
In Integration, select Lambda function `twin-api` and click Next.

After that, set up routes for the API:

```text
Method: ANY
Path: /{proxy+}
Target: twin-api

Method: GET
Path: /health
Target: twin-api

Method: POST
Path: /chat
Target: twin-api

Method: OPTIONS
Path: /{proxy+}
Target: twin-api
```

After route setup, update CORS settings:

```text
Access-Control-Allow-Origin: Type * and click Add (important: click Add)
Access-Control-Allow-Headers: Type * and click Add
Access-Control-Allow-Methods: Type * and click Add (or add GET, POST, OPTIONS)
Access-Control-Max-Age: 300
```

After that, test the API. You can get the API endpoint from API details -> Invoke URL.

### Frontend

Now lets deploy the frontend to S3 as a static website.
For this, create another S3 bucket named `twin-agenticapp-fe` and update
bucket policy to allow public read of objects.

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "PublicReadGetObject",
			"Effect": "Allow",
			"Principal": "*",
			"Action": "s3:GetObject",
			"Resource": "arn:aws:s3:::twin-agenticapp-fe/*"
		}
	]
}
```

After that, run the following commands in `frontend`:

```bash
# build the frontend project
npm run build
# upload/sync the build files to s3 bucket
aws s3 sync out/ s3://twin-agenticapp-fe/ --delete
```

Before creating a release build, make sure `next.config.ts` enables static export:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
	output: "export",
	images: {
		unoptimized: true,
	},
};

export default nextConfig;
```

After build artifacts are uploaded, enable static website hosting in bucket properties.

#### Lets setup the CloudFront Distribution For Frontend

We are going to use CloudFront Distribution as a caching layer for the static site hosted on S3.

Create a new CloudFront distribution with:

```text
name: twin-distribution
```

On origin, select Other and enter the domain name from the S3 static website
without `https`, and provide origin name `s3-static-web` (or keep default).
Set origin protocol policy to `HTTP only`.

Set cache behavior as needed for wildcard paths (`*`).
You can disable WAF integration to reduce cost.

Select price class `North America and Europe` to reduce cost.
After distribution is created, add the CloudFront domain to Lambda CORS allowed origins.

> [!NOTE]
> Make sure to invalidate cache after updating CloudFront settings.

## Using AWS Bedrock for AI Models

We can also use AWS Bedrock for AI models instead of OpenAI.
First, create the Bedrock client.

```python
bedrock_client = boto3.client(
		service_name="bedrock-runtime",
		region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")
)
```

After that, use the client to call AI models.

```python
response = bedrock_client.converse(
		modelId=BEDROCK_MODEL_ID,
		messages=messages,
		inferenceConfig={
				"maxTokens": 2000,
				"temperature": 0.7,
				"topP": 0.9,
		},
)

# Extract response text
return response["output"]["message"]["content"][0]["text"]
```

> [!NOTE]
> Add Bedrock permissions to the Lambda function execution role.
