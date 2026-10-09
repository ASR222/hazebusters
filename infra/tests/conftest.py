import os
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA / "processor"))
os.environ.setdefault("AWS_REGION", "ap-south-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "ap-south-1")
os.environ.setdefault("TABLE_NAME", "test-table")
os.environ.setdefault("BUCKET_NAME", "test-bucket")
