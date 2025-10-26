# Image Upload Service

A production-ready Flask application for uploading images to AWS S3 with a clean UI and RESTful API.

## Features

✅ **Dynamic URL Routes** - Access upload page via `base_url/<image_id>`  
✅ **S3 Storage** - Secure image uploads to AWS S3  
✅ **SQLite Database** - Track uploaded images with metadata  
✅ **RESTful API** - Retrieve S3 URLs by image ID  
✅ **Beautiful UI** - Modern, responsive upload interface  
✅ **Production Ready** - Structured logging, error handling, health checks  
✅ **Docker Support** - Easy deployment with Docker Compose  

## Tech Stack

- **Backend**: Flask (Python 3.11+)
- **Storage**: AWS S3
- **Database**: SQLite
- **Package Manager**: uv (ultra-fast Python package installer)
- **Containerization**: Docker & Docker Compose

---

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker & Docker Compose installed
- AWS S3 bucket created
- AWS credentials with S3 access

### 1. Clone and Configure

```bash
# Create .env file from example
cp .env.example .env

# Edit .env with your AWS credentials
nano .env
```

### 2. Run with Docker Compose

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

The application will be available at `http://localhost:5000`

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- uv package manager
- AWS S3 bucket and credentials

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### 2. Setup Environment

```bash
# Create .env file
cp .env.example .env

# Edit with your AWS credentials
nano .env
```

### 3. Install Dependencies

```bash
# Using uv (fast!)
uv pip install .

# Or with virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install .

# Install with dev dependencies
uv pip install -e ".[dev]"
```

### 4. Run Application

```bash
python app.py
```

Application starts at `http://localhost:5000`

---

## Environment Variables

Create a `.env` file with the following configuration:

```bash
# AWS Configuration (REQUIRED)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_BUCKET_NAME=your_bucket_name
AWS_REGION=us-east-1

# Application Configuration
ENVIRONMENT=production  # or 'development'
PORT=5000
SECRET_KEY=your_random_secret_key_here

# File Upload Configuration
MAX_FILE_SIZE=10485760  # 10MB in bytes

# Database Configuration
DATABASE_PATH=images.db

# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

---

## AWS S3 Setup

### 1. Create S3 Bucket

```bash
aws s3 mb s3://your-bucket-name --region us-east-1
```

### 2. Set Bucket Policy (Public Read Access)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

### 3. Configure CORS (if accessing from different domain)

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["*"],
    "ExposeHeaders": []
  }
]
```

### 4. IAM User Permissions

Your AWS user needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::your-bucket-name"
    }
  ]
}
```

---

## API Endpoints

### 1. Upload Page (UI)

```
GET /<image_id>
```

**Example**: `http://localhost:5000/user123`

Opens upload interface for the specified ID.

### 2. Upload Image

```
POST /upload/<image_id>
```

**Request**: Multipart form data with `file` field

**Response**:
```json
{
  "success": true,
  "message": "Image uploaded successfully",
  "image_id": "user123",
  "s3_url": "https://bucket.s3.region.amazonaws.com/uploads/user123/abc123.jpg",
  "uploaded_at": "2025-10-26T10:30:00.000000"
}
```

### 3. Get Latest Image URL

```
GET /api/url/<image_id>
```

**Response**:
```json
{
  "success": true,
  "image_id": "user123",
  "s3_url": "https://bucket.s3.region.amazonaws.com/uploads/user123/abc123.jpg",
  "original_filename": "photo.jpg",
  "file_size": 524288,
  "content_type": "image/jpeg",
  "uploaded_at": "2025-10-26T10:30:00.000000"
}
```

### 4. Get All Images for ID

```
GET /api/images/<image_id>
```

Returns all uploads for a given ID (if multiple uploads exist).

### 5. Health Check

```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-26T10:30:00.000000",
  "environment": "production"
}
```

---

## File Upload Specifications

- **Allowed Formats**: PNG, JPG, JPEG, GIF, WEBP, BMP, TIFF
- **Max File Size**: 10MB (configurable via `MAX_FILE_SIZE`)
- **Storage**: AWS S3 with unique filenames
- **Metadata**: Original filename, size, content type tracked in SQLite

---

## Docker Commands

### Build & Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Development Mode

Uncomment volume mounts in `docker-compose.yml` for hot reload:

```yaml
volumes:
  - ./app.py:/app/app.py
  - ./templates:/app/templates
```

### Production Deployment

```bash
# Build and run in background
docker-compose up -d --build

# Scale if needed (requires load balancer)
docker-compose up -d --scale app=3
```

---

## Database Schema

### `images` Table

| Column            | Type      | Description                    |
|-------------------|-----------|--------------------------------|
| id                | TEXT      | Image/User ID (Primary Key)   |
| s3_url            | TEXT      | Full S3 URL                    |
| s3_key            | TEXT      | S3 object key                  |
| original_filename | TEXT      | Original uploaded filename     |
| file_size         | INTEGER   | File size in bytes             |
| content_type      | TEXT      | MIME type                      |
| uploaded_at       | TIMESTAMP | Upload timestamp (UTC)         |
| metadata          | TEXT      | Additional JSON metadata       |

---

## Logging

Structured JSON logging for production monitoring:

```json
{
  "asctime": "2025-10-26T10:30:00",
  "name": "root",
  "levelname": "INFO",
  "message": "Upload completed successfully for ID: user123"
}
```

Set log level via `LOG_LEVEL` environment variable:
- `DEBUG`: Detailed debugging
- `INFO`: General information (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical failures

---

## Security Considerations

### ✅ Implemented

- ✅ Input validation (file type, size, ID format)
- ✅ Secure filename handling
- ✅ Environment variable configuration
- ✅ Error handling without sensitive data exposure
- ✅ CORS ready (configure as needed)
- ✅ Health checks for monitoring

### 🔐 Production Recommendations

1. **HTTPS**: Use reverse proxy (Nginx/Traefik) with SSL
2. **Rate Limiting**: Add Flask-Limiter for API protection
3. **Authentication**: Add JWT/OAuth if needed
4. **Private S3**: Use signed URLs instead of public access
5. **File Scanning**: Add virus scanning for uploads
6. **Monitoring**: Integrate with Prometheus/Grafana
7. **Backup**: Regular database backups
8. **Secrets**: Use AWS Secrets Manager or HashiCorp Vault

---

## Deployment

### Docker (Recommended)

```bash
# Production deployment
docker-compose up -d --build

# With custom port
PORT=8080 docker-compose up -d
```

### Cloud Platforms

#### **AWS ECS/Fargate**

1. Push image to ECR
2. Create ECS task definition
3. Deploy as service

#### **Google Cloud Run**

```bash
gcloud run deploy image-upload-service \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### **Heroku**

```bash
heroku create your-app-name
heroku config:set AWS_ACCESS_KEY_ID=xxx
heroku config:set AWS_SECRET_ACCESS_KEY=xxx
heroku config:set AWS_BUCKET_NAME=xxx
git push heroku main
```

#### **DigitalOcean App Platform**

1. Connect GitHub repo
2. Set environment variables
3. Deploy

---

## Monitoring & Maintenance

### Health Check

```bash
curl http://localhost:5000/health
```

### View Logs (Docker)

```bash
# Real-time logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Database Backup

```bash
# Copy from container
docker cp image-upload-service:/app/data/images.db ./backup-$(date +%Y%m%d).db

# Or if running locally
cp images.db backup-$(date +%Y%m%d).db
```

### Database Query

```bash
# Access database
sqlite3 images.db

# View all records
SELECT * FROM images;

# Count uploads per ID
SELECT id, COUNT(*) as count FROM images GROUP BY id;
```

---

## Troubleshooting

### Issue: AWS Credentials Invalid

```bash
# Test AWS credentials
aws s3 ls s3://your-bucket-name

# Verify environment variables
docker-compose exec app env | grep AWS
```

### Issue: Database Locked

```bash
# Stop container
docker-compose down

# Remove database (will lose data!)
rm data/images.db

# Restart
docker-compose up -d
```

### Issue: Port Already in Use

```bash
# Use different port
PORT=8080 docker-compose up -d
```

### Issue: File Upload Fails

- Check S3 bucket permissions
- Verify file size < MAX_FILE_SIZE
- Check allowed file extensions
- View logs: `docker-compose logs -f`

---

## Development

### Running Tests

```bash
# Install dev dependencies
uv pip install pytest pytest-cov requests

# Run tests (coming soon)
pytest tests/
```

### Code Formatting

```bash
# Install black
uv pip install black

# Format code
black app.py
```

---

## Project Structure

```
upload_s3/
├── app.py                 # Main Flask application
├── pyproject.toml        # Project config & dependencies (uv)
├── Dockerfile            # Container definition
├── docker-compose.yml    # Docker Compose config
├── .env.example          # Environment template
├── .gitignore           # Git ignore rules
├── .dockerignore        # Docker ignore rules
├── README.md            # This file
├── templates/
│   └── upload.html      # Upload UI
└── data/                # Database directory (created at runtime)
    └── images.db        # SQLite database
```

---

## License

MIT License - feel free to use in your projects!

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review logs: `docker-compose logs -f`
3. Verify AWS credentials and S3 permissions
4. Check environment variables

---

## Performance Tips

- Use CloudFront CDN in front of S3
- Enable S3 Transfer Acceleration
- Use appropriate S3 storage class
- Index database for faster queries
- Consider Redis for caching (future enhancement)

---

## Future Enhancements

- [ ] Image resizing/optimization
- [ ] Multiple file upload
- [ ] Progress bar for large files
- [ ] Admin dashboard
- [ ] User authentication
- [ ] File deletion API
- [ ] Thumbnail generation
- [ ] Webhook notifications
- [ ] PostgreSQL support
- [ ] Redis caching

---

**Built with ❤️ using Flask, uv, and Docker**

