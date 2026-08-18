# Deployment Guide — OAN Catalogue Master Data Management

This guide covers every step required to deploy the full **OAN Catalogue MDM** stack to AWS, from provisioning infrastructure through to a running, production-ready system. Read it end-to-end before starting.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Prerequisites](#2-prerequisites)
3. [AWS Infrastructure Provisioning](#3-aws-infrastructure-provisioning)
   - 3.1 [VPC & Networking](#31-vpc--networking)
   - 3.2 [RDS PostgreSQL](#32-rds-postgresql)
   - 3.3 [EC2 Instance (Docker Compose deployment)](#33-ec2-instance-docker-compose-deployment)
   - 3.4 [ECR — Container Registry](#34-ecr--container-registry)
   - 3.5 [Security Groups](#35-security-groups)
   - 3.6 [IAM Roles & Policies](#36-iam-roles--policies)
   - 3.7 [ALB — Application Load Balancer](#37-alb--application-load-balancer)
   - 3.8 [ACM — TLS Certificate](#38-acm--tls-certificate)
   - 3.9 [Route 53 DNS](#39-route-53-dns)
4. [Build & Push Docker Images](#4-build--push-docker-images)
5. [Database Initialisation](#5-database-initialisation)
6. [Configure Environment on EC2](#6-configure-environment-on-ec2)
7. [Deploy the API Service](#7-deploy-the-api-service)
8. [Deploy the Next.js Frontend](#8-deploy-the-nextjs-frontend)
9. [Verify the Deployment](#9-verify-the-deployment)
10. [Monitoring & Metrics](#10-monitoring--metrics)
11. [Maintenance Operations](#11-maintenance-operations)
12. [Security Hardening Checklist](#12-security-hardening-checklist)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Architecture Overview

```
Internet
    │
    ▼
[Route 53] ──► [ALB (HTTPS 443)] ──► [EC2 / ECS target group]
                                          │
                         ┌────────────────┼──────────────────┐
                         │                │                  │
                    [API container]  [Next.js container]  [Nginx/reverse proxy]
                         │
                    [RDS PostgreSQL 16]
```

**Components deployed:**

| Component | Technology | Default Port |
|---|---|---|
| Catalogue REST API | Python FastAPI / Gunicorn + Uvicorn | 8000 |
| Admin Web Frontend | Next.js 16 (Node.js server) | 3000 |
| Database | AWS RDS PostgreSQL 16 | 5432 |
| Container runtime | Docker (Docker Compose on EC2) | — |
| TLS termination | AWS ALB | 443 |

---

## 2. Prerequisites

Install and configure the following on your **local machine** before proceeding.

### 2.1 Local Tooling

```bash
# AWS CLI v2
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o AWSCLIV2.pkg
sudo installer -pkg AWSCLIV2.pkg -target /
aws --version   # aws-cli/2.x.x

# Docker Desktop (or Docker Engine)
docker --version        # Docker 24+
docker compose version  # v2.x

# Node.js 20 LTS (for local Next.js build if needed)
node --version  # v20.x

# Python 3.11+ (for local catalogue-api build if needed)
python3 --version  # 3.11+
```

### 2.2 AWS Account & Credentials

```bash
aws configure
# AWS Access Key ID:     <your-access-key>
# AWS Secret Access Key: <your-secret-key>
# Default region:        eu-west-1        # change to your preferred region
# Default output format: json
```

Confirm access:

```bash
aws sts get-caller-identity
```

### 2.3 Domain Name

You must own or control a domain whose DNS you can manage (either through Route 53 or an external registrar with CNAME delegation).

---

## 3. AWS Infrastructure Provisioning

> All commands below use `eu-west-1`. Replace with your target region throughout.

### 3.1 VPC & Networking

Create a dedicated VPC with public and private subnets across two Availability Zones.

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --query 'Vpc.VpcId' --output text)
aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=catalogue-vpc

# Enable DNS hostnames (required for RDS endpoint resolution)
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames

# Public subnet A (for ALB and EC2)
SUBNET_PUB_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 \
  --availability-zone eu-west-1a \
  --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $SUBNET_PUB_A --tags Key=Name,Value=catalogue-public-a

# Public subnet B (ALB requires 2 AZs)
SUBNET_PUB_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 \
  --availability-zone eu-west-1b \
  --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $SUBNET_PUB_B --tags Key=Name,Value=catalogue-public-b

# Private subnet A (for RDS)
SUBNET_PRIV_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.3.0/24 \
  --availability-zone eu-west-1a \
  --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $SUBNET_PRIV_A --tags Key=Name,Value=catalogue-private-a

# Private subnet B (RDS requires 2 AZs for subnet group)
SUBNET_PRIV_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID --cidr-block 10.0.4.0/24 \
  --availability-zone eu-west-1b \
  --query 'Subnet.SubnetId' --output text)
aws ec2 create-tags --resources $SUBNET_PRIV_B --tags Key=Name,Value=catalogue-private-b

# Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID

# Route table for public subnets
RTB_PUB=$(aws ec2 create-route-table --vpc-id $VPC_ID \
  --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id $RTB_PUB \
  --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 associate-route-table --route-table-id $RTB_PUB --subnet-id $SUBNET_PUB_A
aws ec2 associate-route-table --route-table-id $RTB_PUB --subnet-id $SUBNET_PUB_B

# Auto-assign public IPs in public subnets
aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_PUB_A --map-public-ip-on-launch
aws ec2 modify-subnet-attribute \
  --subnet-id $SUBNET_PUB_B --map-public-ip-on-launch
```

### 3.2 RDS PostgreSQL

**Create DB subnet group:**

```bash
aws rds create-db-subnet-group \
  --db-subnet-group-name catalogue-db-subnet \
  --db-subnet-group-description "Catalogue MDM private DB subnets" \
  --subnet-ids $SUBNET_PRIV_A $SUBNET_PRIV_B
```

**Security group for RDS (only allow EC2 access):**

```bash
SG_RDS=$(aws ec2 create-security-group \
  --group-name catalogue-rds-sg \
  --description "Catalogue RDS security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)
```

> You will add an inbound rule from the EC2 security group after creating it in [Section 3.5](#35-security-groups).

**Create RDS instance:**

```bash
aws rds create-db-instance \
  --db-instance-identifier catalogue-postgres \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16.3 \
  --allocated-storage 20 \
  --storage-type gp3 \
  --storage-encrypted \
  --db-name catalogue \
  --master-username catalogue_admin \
  --master-user-password "<STRONG_PASSWORD>" \
  --vpc-security-group-ids $SG_RDS \
  --db-subnet-group-name catalogue-db-subnet \
  --backup-retention-period 7 \
  --preferred-backup-window "02:00-03:00" \
  --preferred-maintenance-window "Mon:03:00-Mon:04:00" \
  --no-publicly-accessible \
  --deletion-protection \
  --tags Key=Name,Value=catalogue-postgres
```

Wait for the instance to become available (takes ~5–10 minutes):

```bash
aws rds wait db-instance-available \
  --db-instance-identifier catalogue-postgres

# Capture the endpoint hostname for later use
RDS_HOST=$(aws rds describe-db-instances \
  --db-instance-identifier catalogue-postgres \
  --query 'DBInstances[0].Endpoint.Address' --output text)
echo "RDS endpoint: $RDS_HOST"
```

**Create the application database user** (connect via a bastion or from the EC2 instance after SSH):

```sql
-- Run these SQL commands on the RDS instance
CREATE USER catalogue WITH PASSWORD '<APP_DB_PASSWORD>';
CREATE DATABASE catalogue OWNER catalogue;
GRANT ALL PRIVILEGES ON DATABASE catalogue TO catalogue;
```

### 3.3 EC2 Instance (Docker Compose deployment)

**Create an SSH key pair:**

```bash
aws ec2 create-key-pair \
  --key-name catalogue-key \
  --query 'KeyMaterial' --output text > ~/.ssh/catalogue-key.pem
chmod 400 ~/.ssh/catalogue-key.pem
```

**Launch EC2 instance:**

```bash
# Use Amazon Linux 2023 (x86_64) — check latest AMI for your region
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*-x86_64" \
            "Name=state,Values=available" \
  --query 'sort_by(Images,&CreationDate)[-1].ImageId' \
  --output text)

INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.medium \
  --key-name catalogue-key \
  --subnet-id $SUBNET_PUB_A \
  --security-group-ids $SG_EC2 \
  --iam-instance-profile Name=catalogue-ec2-profile \
  --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30,"VolumeType":"gp3","Encrypted":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=catalogue-app}]' \
  --query 'Instances[0].InstanceId' --output text)

aws ec2 wait instance-running --instance-ids $INSTANCE_ID

EC2_PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
echo "EC2 IP: $EC2_PUBLIC_IP"
```

> **Note:** `$SG_EC2` and the IAM instance profile are created in the next two sections. If creating interactively, create those first then substitute the IDs above.

**SSH into the instance and install Docker:**

```bash
ssh -i ~/.ssh/catalogue-key.pem ec2-user@$EC2_PUBLIC_IP

# On the EC2 instance:
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user

# Install Docker Compose v2 plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL \
  https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version

# Log out and back in to apply the docker group
exit
ssh -i ~/.ssh/catalogue-key.pem ec2-user@$EC2_PUBLIC_IP
```

**Install Node.js 20 (for the Next.js server process):**

```bash
# On the EC2 instance:
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
node --version   # v20.x
```

### 3.4 ECR — Container Registry

Create three ECR repositories — one per Docker image:

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=eu-west-1

for repo in catalogue-api catalogue-db-migration catalogue-db-seed; do
  aws ecr create-repository \
    --repository-name openg2p-catalogue/$repo \
    --image-scanning-configuration scanOnPush=true \
    --encryption-configuration encryptionType=AES256 \
    --region $AWS_REGION
done
```

### 3.5 Security Groups

**EC2 security group:**

```bash
SG_EC2=$(aws ec2 create-security-group \
  --group-name catalogue-ec2-sg \
  --description "Catalogue EC2 app security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

# Allow SSH from your IP only
MY_IP=$(curl -s https://checkip.amazonaws.com)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_EC2 \
  --protocol tcp --port 22 --cidr ${MY_IP}/32

# Allow ALB to reach the API (port 8000) and Next.js (port 3000)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_EC2 \
  --protocol tcp --port 8000 --source-group $SG_ALB

aws ec2 authorize-security-group-ingress \
  --group-id $SG_EC2 \
  --protocol tcp --port 3000 --source-group $SG_ALB

# Allow all outbound (needed to pull images from ECR, reach RDS)
# (This is the default; verify it exists)
aws ec2 describe-security-groups --group-ids $SG_EC2 \
  --query 'SecurityGroups[0].IpPermissionsEgress'
```

**ALB security group:**

```bash
SG_ALB=$(aws ec2 create-security-group \
  --group-name catalogue-alb-sg \
  --description "Catalogue ALB security group" \
  --vpc-id $VPC_ID \
  --query 'GroupId' --output text)

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ALB \
  --protocol tcp --port 80 --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $SG_ALB \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

**Allow EC2 to reach RDS:**

```bash
aws ec2 authorize-security-group-ingress \
  --group-id $SG_RDS \
  --protocol tcp --port 5432 \
  --source-group $SG_EC2
```

### 3.6 IAM Roles & Policies

Create a role that allows the EC2 instance to pull images from ECR and read Secrets Manager:

```bash
# Trust policy
cat > /tmp/ec2-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "ec2.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name catalogue-ec2-role \
  --assume-role-policy-document file:///tmp/ec2-trust.json

# Attach managed policies
aws iam attach-role-policy \
  --role-name catalogue-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

aws iam attach-role-policy \
  --role-name catalogue-ec2-role \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Create instance profile and attach role
aws iam create-instance-profile \
  --instance-profile-name catalogue-ec2-profile

aws iam add-role-to-instance-profile \
  --instance-profile-name catalogue-ec2-profile \
  --role-name catalogue-ec2-role

# Attach profile to running instance (if not done at launch)
aws ec2 associate-iam-instance-profile \
  --instance-id $INSTANCE_ID \
  --iam-instance-profile Name=catalogue-ec2-profile
```

### 3.7 ALB — Application Load Balancer

```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name catalogue-alb \
  --subnets $SUBNET_PUB_A $SUBNET_PUB_B \
  --security-groups $SG_ALB \
  --scheme internet-facing \
  --type application \
  --ip-address-type ipv4 \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)
echo "ALB DNS: $ALB_DNS"

# Target group for the API (port 8000)
TG_API=$(aws elbv2 create-target-group \
  --name catalogue-api-tg \
  --protocol HTTP --port 8000 \
  --vpc-id $VPC_ID \
  --target-type instance \
  --health-check-path /health/ready \
  --health-check-interval-seconds 15 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Target group for the Next.js frontend (port 3000)
TG_WEB=$(aws elbv2 create-target-group \
  --name catalogue-web-tg \
  --protocol HTTP --port 3000 \
  --vpc-id $VPC_ID \
  --target-type instance \
  --health-check-path / \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

# Register EC2 instance in both target groups
aws elbv2 register-targets \
  --target-group-arn $TG_API \
  --targets Id=$INSTANCE_ID

aws elbv2 register-targets \
  --target-group-arn $TG_WEB \
  --targets Id=$INSTANCE_ID
```

Listener rules (configured after ACM certificate is issued in [Section 3.8](#38-acm--tls-certificate)):

```bash
# HTTPS listener with path-based routing
LISTENER_ARN=$(aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTPS --port 443 \
  --certificates CertificateArn=$ACM_CERT_ARN \
  --default-actions Type=forward,TargetGroupArn=$TG_WEB \
  --query 'Listeners[0].ListenerArn' --output text)

# Route /api/* and / paths to the API target group
aws elbv2 create-rule \
  --listener-arn $LISTENER_ARN \
  --priority 10 \
  --conditions '[{"Field":"path-pattern","Values":["/api/*","/docs","/redoc","/openapi.json","/health/*","/metrics"]}]' \
  --actions Type=forward,TargetGroupArn=$TG_API

# HTTP → HTTPS redirect
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP --port 80 \
  --default-actions \
    Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'
```

### 3.8 ACM — TLS Certificate

```bash
ACM_CERT_ARN=$(aws acm request-certificate \
  --domain-name catalogue.example.org \
  --subject-alternative-names "*.catalogue.example.org" \
  --validation-method DNS \
  --query 'CertificateArn' --output text)

# Retrieve the DNS validation record
aws acm describe-certificate \
  --certificate-arn $ACM_CERT_ARN \
  --query 'Certificate.DomainValidationOptions'
```

Add the CNAME record shown in the output to your DNS provider (or Route 53 — see next section). Wait for the certificate status to become `ISSUED`:

```bash
aws acm wait certificate-validated --certificate-arn $ACM_CERT_ARN
```

### 3.9 Route 53 DNS

If using Route 53, create an alias record pointing to the ALB:

```bash
HOSTED_ZONE_ID=<YOUR_HOSTED_ZONE_ID>

aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "catalogue.example.org",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z32O12XQLNTSW2",
          "DNSName": "'"$ALB_DNS"'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

> `Z32O12XQLNTSW2` is the hosted zone ID for ALB in `eu-west-1`. Refer to [AWS documentation](https://docs.aws.amazon.com/general/latest/gr/elb.html) for other regions.

---

## 4. Build & Push Docker Images

Run these steps from your **local machine** in the root of this repository.

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=eu-west-1
ECR_BASE=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Authenticate Docker with ECR
aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ECR_BASE

# Build all three images
docker build \
  -t catalogue-api \
  -f docker/catalogue-api/Dockerfile \
  --build-arg FASTAPI_COMMON_REF=b11fac39f8db6dc12581bf14d179c67ed5bce672 \
  --build-arg IAM_SERVICE_REF=49ba8905922ded93e9011f4ea0630a627653939b \
  .

docker build \
  -t catalogue-db-migration \
  -f docker/db-migration/Dockerfile \
  .

docker build \
  -t catalogue-db-seed \
  -f docker/db-seed/Dockerfile.sql \
  .

# Tag and push
IMAGE_TAG=0.2.0   # or use $(git rev-parse --short HEAD)

for img in catalogue-api catalogue-db-migration catalogue-db-seed; do
  docker tag $img \
    ${ECR_BASE}/openg2p-catalogue/${img}:${IMAGE_TAG}
  docker tag $img \
    ${ECR_BASE}/openg2p-catalogue/${img}:latest
  docker push ${ECR_BASE}/openg2p-catalogue/${img}:${IMAGE_TAG}
  docker push ${ECR_BASE}/openg2p-catalogue/${img}:latest
done
```

---

## 5. Database Initialisation

This step runs the **14 SQL migrations** and loads seed data. It must run once before starting the API.

### 5.1 Store Secrets in AWS Secrets Manager

```bash
# Store the application DB credentials
aws secretsmanager create-secret \
  --name catalogue/db-credentials \
  --description "Catalogue MDM database credentials" \
  --secret-string '{
    "host": "'"$RDS_HOST"'",
    "port": "5432",
    "dbname": "catalogue",
    "username": "catalogue",
    "password": "<APP_DB_PASSWORD>"
  }'
```

### 5.2 Run Migrations from EC2

SSH into the EC2 instance:

```bash
ssh -i ~/.ssh/catalogue-key.pem ec2-user@$EC2_PUBLIC_IP
```

On the instance, authenticate with ECR and run the migration container:

```bash
AWS_REGION=eu-west-1
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

aws ecr get-login-password --region $AWS_REGION \
  | docker login --username AWS --password-stdin $ECR_BASE

# Run migrations
docker run --rm \
  -e PGHOST=<RDS_ENDPOINT> \
  -e PGPORT=5432 \
  -e PGDATABASE=catalogue \
  -e PGUSER=catalogue \
  -e PGPASSWORD=<APP_DB_PASSWORD> \
  ${ECR_BASE}/openg2p-catalogue/catalogue-db-migration:latest \
  --expected-version 014
```

Expected output: each migration file (001 through 014) applied and confirmed.

### 5.3 Run Data Seed

```bash
docker run --rm \
  -e PGHOST=<RDS_ENDPOINT> \
  -e PGPORT=5432 \
  -e PGDATABASE=catalogue \
  -e PGUSER=catalogue \
  -e PGPASSWORD=<APP_DB_PASSWORD> \
  ${ECR_BASE}/openg2p-catalogue/catalogue-db-seed:latest \
  --manifest /seed/sql/manifest.yaml \
  --expected-country ETH \
  --trigger MANUAL
```

---

## 6. Configure Environment on EC2

### 6.1 Clone the Repository

```bash
# On the EC2 instance
git clone https://github.com/<your-org>/oan_catalog_master_data_management.git /opt/catalogue
cd /opt/catalogue
```

### 6.2 Create the Production .env File

```bash
cat > /opt/catalogue/.env <<'EOF'
# ── Database ───────────────────────────────────────────────────────────────
CATALOGUE_DB=catalogue
CATALOGUE_DB_USER=catalogue
CATALOGUE_DB_PASSWORD=<APP_DB_PASSWORD>
CATALOGUE_DB_PORT=5432

# ── API container ──────────────────────────────────────────────────────────
CATALOGUE_API_DB_HOSTNAME=<RDS_ENDPOINT>
CATALOGUE_API_DB_PORT=5432
CATALOGUE_API_DB_DBNAME=catalogue
CATALOGUE_API_DB_USERNAME=catalogue
CATALOGUE_API_DB_PASSWORD=<APP_DB_PASSWORD>
CATALOGUE_API_DEFAULT_COUNTRY_CODE=ETH
CATALOGUE_API_EXPECTED_SCHEMA_VERSION=014
CATALOGUE_API_NO_OF_WORKERS=4
CATALOGUE_API_DEV_MODE=false
CATALOGUE_API_CACHE_EXPIRE_SECONDS=300
CATALOGUE_API_PORT=8000

# ── Country / seed ─────────────────────────────────────────────────────────
CATALOGUE_COUNTRY_CODE=ETH

# ── Next.js frontend ───────────────────────────────────────────────────────
CATALOGUE_API_BASE_URL=https://catalogue.example.org

# ── Prometheus (multi-process) ─────────────────────────────────────────────
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus

# ── Docker images ──────────────────────────────────────────────────────────
CATALOGUE_IMAGE=<AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/openg2p-catalogue/catalogue-api
CATALOGUE_IMAGE_TAG=0.2.0
EOF

chmod 600 /opt/catalogue/.env
```

> **Important:** Never commit this `.env` file to source control. The `.env.example` in the repository is a safe template; the real credentials live here and in Secrets Manager only.

### 6.3 Create a Production Docker Compose Override

Create `/opt/catalogue/compose.prod.yaml` to override the local dev defaults:

```yaml
# compose.prod.yaml
name: openg2p-catalogue

services:
  api:
    image: ${CATALOGUE_IMAGE}:${CATALOGUE_IMAGE_TAG}
    environment:
      CATALOGUE_API_DEV_MODE: "false"
      CATALOGUE_API_NO_OF_WORKERS: "4"
    restart: always
    logging:
      driver: awslogs
      options:
        awslogs-region: eu-west-1
        awslogs-group: /catalogue/api
        awslogs-stream-prefix: api

  # Remove local postgres — point to RDS instead
  postgres:
    deploy:
      replicas: 0
```

> The `awslogs` driver streams container logs directly to CloudWatch Logs. Create the log group first:
>
> ```bash
> aws logs create-log-group --log-group-name /catalogue/api
> aws logs put-retention-policy \
>   --log-group-name /catalogue/api \
>   --retention-in-days 30
> ```

---

## 7. Deploy the API Service

### 7.1 Start the API Container

```bash
cd /opt/catalogue

# Pull the production image
docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  --env-file .env \
  pull api

# Start only the API (DB is on RDS; migrations already ran)
docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  --env-file .env \
  up -d api
```

### 7.2 Verify API Health

```bash
curl -s http://localhost:8000/health/ready
# Expected: {"status":"ok"} or similar 200 response
```

```bash
# Check logs
docker compose -f compose.yaml -f compose.prod.yaml logs -f api
```

---

## 8. Deploy the Next.js Frontend

The Next.js frontend requires a **build step** and then runs as a Node.js server process.

### 8.1 Build the Frontend on EC2

```bash
cd /opt/catalogue/web

# Install production dependencies
npm ci

# Set the API base URL at build time (Next.js bakes env into the build)
export CATALOGUE_API_BASE_URL=https://catalogue.example.org
export NEXT_PUBLIC_API_BASE_URL=https://catalogue.example.org

# If the frontend connects directly to Postgres for dashboard charts,
# set the DATABASE_URL so it targets RDS (not localhost):
export DATABASE_URL=postgresql://catalogue:<APP_DB_PASSWORD>@<RDS_ENDPOINT>:5432/catalogue

npm run build
```

### 8.2 Run the Next.js Server as a Systemd Service

```bash
# Create the systemd unit
sudo tee /etc/systemd/system/catalogue-web.service <<'EOF'
[Unit]
Description=Catalogue MDM Next.js Frontend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/catalogue/web
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=CATALOGUE_API_BASE_URL=https://catalogue.example.org
Environment=DATABASE_URL=postgresql://catalogue:<APP_DB_PASSWORD>@<RDS_ENDPOINT>:5432/catalogue
ExecStart=/usr/bin/node /opt/catalogue/web/.next/standalone/server.js
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable catalogue-web
sudo systemctl start catalogue-web
sudo systemctl status catalogue-web
```

> **Standalone output mode:** Next.js 16 produces a `standalone` output by default when `output: 'standalone'` is set in `next.config.ts`. If it is not already set, add it:
>
> ```ts
> // web/next.config.ts
> const nextConfig: NextConfig = {
>   output: 'standalone',
> };
> export default nextConfig;
> ```
>
> Then rebuild with `npm run build`.

### 8.3 Verify Frontend

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
# Expected: 200
```

---

## 9. Verify the Deployment

### 9.1 End-to-End Health Checks

```bash
# API health (via ALB / public DNS)
curl -s https://catalogue.example.org/health/ready

# OpenAPI docs are accessible
curl -s -o /dev/null -w "%{http_code}" https://catalogue.example.org/docs
# Expected: 200

# Frontend loads
curl -s -o /dev/null -w "%{http_code}" https://catalogue.example.org/
# Expected: 200

# Prometheus metrics endpoint (internal only — from EC2)
curl -s http://localhost:8000/metrics | head -20
```

### 9.2 Run the Consumer Smoke Test

From local machine:

```bash
# Set the real API URL and an IAM token URL
export CATALOGUE_SERVICE_URL=https://catalogue.example.org
export IAM_TOKEN_URL=<YOUR_IAM_OIDC_TOKEN_ENDPOINT>
export CATALOGUE_COUNTRY_CODE=ETH

docker compose \
  -f compose.consumer.yaml \
  --env-file .env \
  up --build --abort-on-container-exit consumer-smoke
```

A clean run confirms that the API is accepting authenticated requests and returning well-formed data.

---

## 10. Monitoring & Metrics

### 10.1 CloudWatch Alarms

```bash
# CPU utilisation alarm on EC2
aws cloudwatch put-metric-alarm \
  --alarm-name catalogue-ec2-high-cpu \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --dimensions Name=InstanceId,Value=$INSTANCE_ID \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:<REGION>:<ACCOUNT_ID>:catalogue-alerts

# RDS storage alarm
aws cloudwatch put-metric-alarm \
  --alarm-name catalogue-rds-low-storage \
  --metric-name FreeStorageSpace \
  --namespace AWS/RDS \
  --dimensions Name=DBInstanceIdentifier,Value=catalogue-postgres \
  --statistic Average \
  --period 300 \
  --threshold 5368709120 \  # 5 GB
  --comparison-operator LessThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:<REGION>:<ACCOUNT_ID>:catalogue-alerts
```

### 10.2 Prometheus Metrics

The API exposes Prometheus metrics at `GET /metrics`. The relevant environment variable for multi-process mode is:

```
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
```

This directory is mounted as a `tmpfs` in the container (see `compose.yaml`). Ensure it exists and is writable by UID 10001 when running outside Compose:

```bash
mkdir -p /tmp/prometheus
chmod 770 /tmp/prometheus
```

To scrape metrics with a Prometheus server running elsewhere, add a scrape job pointing to `http://<EC2_PRIVATE_IP>:8000/metrics` (accessible within the VPC).

### 10.3 ALB Access Logs

```bash
aws elbv2 modify-load-balancer-attributes \
  --load-balancer-arn $ALB_ARN \
  --attributes \
    Key=access_logs.s3.enabled,Value=true \
    Key=access_logs.s3.bucket,Value=<YOUR_LOG_BUCKET> \
    Key=access_logs.s3.prefix,Value=catalogue-alb
```

---

## 11. Maintenance Operations

### 11.1 Applying a New Schema Migration

```bash
# On EC2, run the migration container against RDS
docker run --rm \
  -e PGHOST=<RDS_ENDPOINT> \
  -e PGPORT=5432 \
  -e PGDATABASE=catalogue \
  -e PGUSER=catalogue \
  -e PGPASSWORD=<APP_DB_PASSWORD> \
  ${ECR_BASE}/openg2p-catalogue/catalogue-db-migration:latest \
  --expected-version <NEW_VERSION>
```

Update `CATALOGUE_API_EXPECTED_SCHEMA_VERSION` in `/opt/catalogue/.env` and restart the API:

```bash
docker compose -f compose.yaml -f compose.prod.yaml --env-file .env restart api
```

### 11.2 Re-Running the Data Seed

The seed is idempotent. Re-run it any time reference data changes:

```bash
docker run --rm \
  -e PGHOST=<RDS_ENDPOINT> \
  -e PGPORT=5432 \
  -e PGDATABASE=catalogue \
  -e PGUSER=catalogue \
  -e PGPASSWORD=<APP_DB_PASSWORD> \
  ${ECR_BASE}/openg2p-catalogue/catalogue-db-seed:latest \
  --manifest /seed/sql/manifest.yaml \
  --expected-country ETH \
  --trigger MANUAL
```

### 11.3 Deploying a New API Image Version

```bash
# From local machine — build, tag, push
docker build -t catalogue-api -f docker/catalogue-api/Dockerfile .
docker tag catalogue-api ${ECR_BASE}/openg2p-catalogue/catalogue-api:0.3.0
docker push ${ECR_BASE}/openg2p-catalogue/catalogue-api:0.3.0

# On EC2 — update IMAGE_TAG in .env, then pull and restart
sed -i 's/CATALOGUE_IMAGE_TAG=.*/CATALOGUE_IMAGE_TAG=0.3.0/' /opt/catalogue/.env

docker compose -f compose.yaml -f compose.prod.yaml --env-file .env pull api
docker compose -f compose.yaml -f compose.prod.yaml --env-file .env up -d api
```

### 11.4 Deploying a New Frontend Version

```bash
# On EC2
cd /opt/catalogue
git pull origin main

cd web
npm ci
npm run build

sudo systemctl restart catalogue-web
sudo systemctl status catalogue-web
```

### 11.5 RDS Snapshots

Manual backup before any destructive operation:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier catalogue-postgres \
  --db-snapshot-identifier catalogue-snapshot-$(date +%Y%m%d)
```

---

## 12. Security Hardening Checklist

- [ ] **Secrets management:** All passwords stored in AWS Secrets Manager; the `.env` on EC2 reads from it (or use [SSM Parameter Store](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html) and fetch at container start).
- [ ] **RDS not publicly accessible:** Confirmed `--no-publicly-accessible` during creation.
- [ ] **Encrypted storage:** RDS storage encrypted (`--storage-encrypted`); EC2 root volume encrypted (`Encrypted: true` in block device mapping).
- [ ] **SSH restricted:** Port 22 open only to your IP (update when IP changes).
- [ ] **Least-privilege IAM:** EC2 role has only `ecr:GetAuthorizationToken`, `ecr:BatchGetImage`, `ecr:GetDownloadUrlForLayer`, and Secrets Manager read.
- [ ] **TLS enforced:** HTTP 80 → HTTPS 301 redirect on ALB; certificate issued via ACM.
- [ ] **Non-root containers:** API runs as UID 10001 (see Dockerfile `USER 10001:10001`).
- [ ] **Read-only root filesystem:** Containers run with `--read-only`; only `/tmp` is writable via `tmpfs`.
- [ ] **Security group principle of least privilege:** RDS only reachable from EC2 security group; no `0.0.0.0/0` inbound on RDS.
- [ ] **Log retention:** CloudWatch log group retention set (e.g., 30 days).
- [ ] **ECR image scanning:** `scanOnPush=true` enabled on all repositories.
- [ ] **Automatic OS patching:** Enable AWS Systems Manager Patch Manager on the EC2 instance.
- [ ] **Deletion protection:** RDS `--deletion-protection` is enabled.
- [ ] **MFA on AWS root account:** Ensure root account has MFA enabled.

---

## 13. Troubleshooting

### API container fails to start — schema version mismatch

```
ERROR: schema version mismatch: expected 014, found 000
```

The migration container has not been run, or failed partway. Check migration logs and re-run [Section 5.2](#52-run-migrations-from-ec2).

### API container cannot connect to RDS

```
asyncpg.exceptions.ConnectionFailureError: could not connect to server
```

1. Verify the security group inbound rule on `$SG_RDS` allows port 5432 from `$SG_EC2`.
2. Confirm `CATALOGUE_API_DB_HOSTNAME` matches the RDS endpoint exactly (no trailing space).
3. Check that the RDS instance status is `available`:
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier catalogue-postgres \
     --query 'DBInstances[0].DBInstanceStatus'
   ```

### ALB health checks failing for the API

1. Confirm the API is listening on port 8000 inside the container:
   ```bash
   docker compose -f compose.yaml -f compose.prod.yaml logs api | tail -20
   ```
2. Confirm the EC2 security group allows inbound from the ALB security group on port 8000.
3. Test the health endpoint locally from EC2:
   ```bash
   curl http://localhost:8000/health/ready
   ```

### Next.js frontend shows blank page or 500

1. Check the systemd service logs:
   ```bash
   sudo journalctl -u catalogue-web -n 100 --no-pager
   ```
2. Ensure `CATALOGUE_API_BASE_URL` is set to the correct HTTPS URL (no trailing slash).
3. If the frontend uses `pg` for direct DB queries (dashboard charts), verify `DATABASE_URL` is correctly set and port 5432 is reachable.

### ECR authentication fails on EC2

```
Error response from daemon: no basic auth credentials
```

The EC2 IAM role may not yet have `ecr:GetAuthorizationToken`. Verify:

```bash
aws iam list-attached-role-policies --role-name catalogue-ec2-role
```

Re-attach `AmazonEC2ContainerRegistryReadOnly` if missing.

### Docker Compose cannot pull the override image

Ensure `compose.prod.yaml` is specified as the second `-f` argument (overrides are applied in order):

```bash
docker compose -f compose.yaml -f compose.prod.yaml ...
```

---

## Summary of Key Variables

| Variable | Where Set | Example Value |
|---|---|---|
| `RDS_ENDPOINT` | AWS Console / CLI | `catalogue-postgres.xxxxxxxx.eu-west-1.rds.amazonaws.com` |
| `APP_DB_PASSWORD` | Secrets Manager | `<strong-random-password>` |
| `ECR_BASE` | Shell / .env | `123456789.dkr.ecr.eu-west-1.amazonaws.com` |
| `IMAGE_TAG` | `.env` | `0.2.0` |
| `CATALOGUE_API_BASE_URL` | `.env` / systemd | `https://catalogue.example.org` |
| `DATABASE_URL` | systemd unit | `postgresql://catalogue:…@<RDS_ENDPOINT>:5432/catalogue` |
| `CATALOGUE_COUNTRY_CODE` | `.env` | `ETH` |
| `CATALOGUE_API_EXPECTED_SCHEMA_VERSION` | `.env` | `014` |
| `CATALOGUE_API_NO_OF_WORKERS` | `.env` | `4` |
| `PROMETHEUS_MULTIPROC_DIR` | `.env` | `/tmp/prometheus` |
