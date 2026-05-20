#!/bin/bash
set -e

export MINIO_ROOT_USER=minioadmin
export MINIO_ROOT_PASSWORD=minioadmin123

export S3_ENDPOINT=http://localhost:9000
export S3_BUCKET=ccbd
export S3_REGION=us-east-1
export S3_ACCESS_KEY=$MINIO_ROOT_USER
export S3_SECRET_KEY=$MINIO_ROOT_PASSWORD

export PATH="/opt/CCBD_Project/.venv/bin:${PATH}"

mkdir -p /data /var/log/minio /root/.mc /opt/CCBD_Project/results /opt/CCBD_Project/benchdownloads /opt/CCBD_Project/data

if ! pgrep -f "minio server /data" > /dev/null 2>&1; then
    nohup minio server /data --console-address ":9001" > /var/log/minio/minio.log 2>&1 &
fi

for i in $(seq 1 60); do
    if curl -fsS "${S3_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! curl -fsS "${S3_ENDPOINT}/minio/health/live" > /dev/null 2>&1; then
    echo "MinIO did not become ready in time."
    echo "Last log lines:"
    tail -n 50 /var/log/minio/minio.log || true
    exit 1
fi

mc alias set local "${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" > /dev/null 2>&1 || true
mc mb "local/${S3_BUCKET}" > /dev/null 2>&1 || true

cat > /etc/profile.d/ccbd-env.sh <<EOF
export S3_ENDPOINT=${S3_ENDPOINT}
export S3_BUCKET=${S3_BUCKET}
export S3_REGION=${S3_REGION}
export S3_ACCESS_KEY=${S3_ACCESS_KEY}
export S3_SECRET_KEY=${S3_SECRET_KEY}
export PATH=/opt/CCBD_Project/.venv/bin:\$PATH
EOF

echo "Environment ready."
echo "Repo: /opt/CCBD_Project"
echo "MinIO S3 API: ${S3_ENDPOINT}"
echo "MinIO console: http://localhost:9001"
echo "Bucket: ${S3_BUCKET}"
echo "Python: $(which python)"
echo "To run:"
echo "cd /opt/CCBD_Project && python bench.py --help"

exec "$@"
