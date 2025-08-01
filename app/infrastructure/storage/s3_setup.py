"""
S3 storage setup and management utilities.
Handles ALL infrastructure concerns for S3 buckets.
"""
import json
import logging
import time
from typing import Dict, Any
from botocore.exceptions import ClientError
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings
from .s3_configurations import S3Configurations

logger = logging.getLogger(__name__)


class S3Setup:
    """
    Manages S3 bucket infrastructure operations.
    
    Responsibilities:
    - Bucket creation and deletion
    - Configuration application (CORS, lifecycle, encryption)
    - Health checks and monitoring
    - Infrastructure validation
    """
    
    def __init__(self):
        self.s3_client = aws_config.s3_client
        self.configs = S3Configurations()
        
        logger.debug("S3Setup initialized", extra={
            "use_local_s3": infra_settings.use_local_s3,
            "endpoint": infra_settings.s3_endpoint_url or "AWS Default"
        })
    
    def setup_all_buckets(self) -> Dict[str, bool]:
        """
        Setup all required buckets for the application.
        
        Returns:
            Dict with bucket setup results
        """
        results = {}
        
        # Setup audio storage bucket
        results['audio'] = self.setup_audio_bucket()
        
        return results
    
    def setup_audio_bucket(self) -> bool:
        """
        Setup the audio storage bucket with complete configuration.
        
        Returns:
            True if setup successful, False otherwise
        """
        bucket_name = infra_settings.s3_bucket_name
        
        try:
            # Create bucket if it doesn't exist
            if not self.bucket_exists(bucket_name):
                logger.info("Creating audio bucket", extra={"bucket_name": bucket_name})
                
                if not self._create_bucket(bucket_name):
                    return False
                
                # Wait for bucket to be available
                self._wait_for_bucket_creation(bucket_name)
            else:
                logger.info("Audio bucket already exists", extra={"bucket_name": bucket_name})
            
            # Apply bucket configuration
            config = self.configs.audio_bucket_config(bucket_name)
            self._apply_bucket_configuration(bucket_name, config)
            
            logger.info("Audio bucket setup completed", extra={
                "bucket_name": bucket_name,
                "features": ["CORS", "Lifecycle", "Encryption", "Versioning"]
            })
            
            return True
            
        except Exception as e:
            logger.error("Failed to setup audio bucket", extra={
                "bucket_name": bucket_name,
                "error": str(e)
            })
            return False
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if bucket exists.
        
        Args:
            bucket_name: Name of the bucket to check
            
        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['404', 'NoSuchBucket']:
                return False
            # Log other errors but don't treat as "doesn't exist"
            logger.warning("Error checking bucket existence", extra={
                "bucket_name": bucket_name,
                "error_code": error_code
            })
            return False
    
    def _create_bucket(self, bucket_name: str) -> bool:
        """
        Create S3 bucket with region-appropriate configuration.
        
        Args:
            bucket_name: Name of the bucket to create
            
        Returns:
            True if creation successful, False otherwise
        """
        try:
            if infra_settings.use_local_s3:
                # MinIO doesn't require region specification
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                # AWS S3 requires region specification for non-us-east-1
                if infra_settings.aws_region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': infra_settings.aws_region
                        }
                    )
            
            logger.info("Bucket created successfully", extra={"bucket_name": bucket_name})
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error("Failed to create bucket", extra={
                "bucket_name": bucket_name,
                "error_code": error_code,
                "error_message": e.response['Error']['Message']
            })
            return False
    
    def _wait_for_bucket_creation(self, bucket_name: str, max_wait_time: int = 60) -> None:
        """
        Wait for bucket to be created and available.
        Uses AWS S3 waiter if available, otherwise falls back to polling (for MinIO).
        Args:
            bucket_name: Name of the bucket
            max_wait_time: Maximum time to wait in seconds
        """
        if infra_settings.use_local_s3:
            # MinIO: Use polling
            start_time = time.time()
            while time.time() - start_time < max_wait_time:
                try:
                    self.s3_client.head_bucket(Bucket=bucket_name)
                    logger.debug("Bucket is available", extra={"bucket_name": bucket_name})
                    return
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code in ['404', 'NoSuchBucket']:
                        time.sleep(1)
                        continue
                    else:
                        raise e
            raise TimeoutError(f"Bucket '{bucket_name}' was not created within {max_wait_time} seconds")
        else:
            # AWS S3: Use waiter
            waiter = self.s3_client.get_waiter('bucket_exists')
            waiter.wait(Bucket=bucket_name, WaiterConfig={"Delay": 2, "MaxAttempts": max_wait_time // 2})
            logger.debug("Bucket is available (AWS waiter)", extra={"bucket_name": bucket_name})
    
    def _apply_bucket_configuration(self, bucket_name: str, config: Dict[str, Any]) -> None:
        """
        Apply complete configuration to bucket.
        
        Args:
            bucket_name: Name of the bucket
            config: Bucket configuration dictionary
        """
        try:
            # Apply CORS configuration
            if 'cors' in config:
                self.s3_client.put_bucket_cors(
                    Bucket=bucket_name,
                    CORSConfiguration=config['cors']
                )
                logger.debug("Applied CORS configuration", extra={"bucket_name": bucket_name})
            
            # Apply lifecycle configuration
            if 'lifecycle' in config:
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration=config['lifecycle']
                )
                logger.debug("Applied lifecycle configuration", extra={"bucket_name": bucket_name})
            
            # Apply encryption configuration
            if 'encryption' in config:
                self.s3_client.put_bucket_encryption(
                    Bucket=bucket_name,
                    ServerSideEncryptionConfiguration=config['encryption']
                )
                logger.debug("Applied encryption configuration", extra={"bucket_name": bucket_name})
            
            # Apply public access block
            if 'public_access_block' in config:
                self.s3_client.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration=config['public_access_block']
                )
                logger.debug("Applied public access block", extra={"bucket_name": bucket_name})
            
            # Apply versioning
            if 'versioning' in config:
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration=config['versioning']
                )
                logger.debug("Applied versioning configuration", extra={"bucket_name": bucket_name})
            
            # Apply tags
            if 'tags' in config:
                self.s3_client.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={'TagSet': config['tags']}
                )
                logger.debug("Applied bucket tags", extra={"bucket_name": bucket_name})
            
            # Apply bucket policy
            if 'bucket_policy' in config:
                self.s3_client.put_bucket_policy(
                    Bucket=bucket_name,
                    Policy=json.dumps(config['bucket_policy'])
                )
                logger.debug("Applied bucket policy", extra={"bucket_name": bucket_name})
                
        except ClientError as e:
            logger.warning("Could not apply some bucket configuration", extra={
                "bucket_name": bucket_name,
                "error_code": e.response['Error']['Code'],
                "error_message": e.response['Error']['Message']
            })
    

    
    def health_check(self) -> Dict[str, Any]:
        """
        Comprehensive S3 health check.
        
        Returns:
            Dictionary with detailed health check results
        """
        results = {
            "service": "s3",
            "status": "unknown",
            "type": "minio" if infra_settings.use_local_s3 else "aws",
            "endpoint": infra_settings.s3_endpoint_url if infra_settings.use_local_s3 else None,
            "region": infra_settings.aws_region
        }
        
        try:
            # Test basic connectivity
            self.s3_client.list_buckets()
            
            # Check required bucket
            bucket_name = infra_settings.s3_bucket_name
            bucket_exists = self.bucket_exists(bucket_name)
            
            if bucket_exists:
                results.update({
                    "status": "healthy",
                    "bucket": bucket_name,
                    "bucket_exists": True
                })
            else:
                results.update({
                    "status": "degraded",
                    "bucket": bucket_name,
                    "bucket_exists": False,
                    "message": f"Required bucket '{bucket_name}' does not exist"
                })
                
        except Exception as e:
            results.update({
                "status": "unhealthy",
                "error": str(e)
            })
        
        return results
    



# Global S3 setup instance
s3_setup = S3Setup()