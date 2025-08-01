"""
S3 bucket configuration templates for Voice Gateway.
Pure data configurations without business logic.
"""
from typing import Dict, Any


class S3Configurations:
    """
    Static S3 bucket configuration templates.
    Contains only configuration data, no business logic.
    """
    
    # CORS Configuration for audio uploads
    AUDIO_BUCKET_CORS = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'HEAD'],
                'AllowedOrigins': ['*'],  # Configure for production
                'ExposeHeaders': ['ETag', 'Content-Length'],
                'MaxAgeSeconds': 3000
            }
        ]
    }
    
    # Lifecycle policies for automatic cleanup
    AUDIO_BUCKET_LIFECYCLE = {
        'Rules': [
            {
                'ID': 'test-files-cleanup',
                'Status': 'Enabled',
                'Filter': {'Prefix': 'test-'},
                'Expiration': {'Days': 7}  # Clean up test files
            },
            {
                'ID': 'incomplete-uploads-cleanup',
                'Status': 'Enabled',
                'Filter': {'Prefix': ''},
                'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 1}
            }
        ]
    }
    
    # Encryption configuration
    AUDIO_BUCKET_ENCRYPTION = {
        'Rules': [
            {
                'ApplyServerSideEncryptionByDefault': {
                    'SSEAlgorithm': 'AES256'
                },
                'BucketKeyEnabled': True
            }
        ]
    }
    
    # Public access block (security)
    AUDIO_BUCKET_PUBLIC_ACCESS_BLOCK = {
        'BlockPublicAcls': True,
        'IgnorePublicAcls': True,
        'BlockPublicPolicy': True,
        'RestrictPublicBuckets': True
    }
    
    # Versioning configuration
    AUDIO_BUCKET_VERSIONING = {
        'Status': 'Enabled'
    }
    
    # Bucket tags
    AUDIO_BUCKET_TAGS = [
        {'Key': 'Project', 'Value': 'VoiceGateway'},
        {'Key': 'Environment', 'Value': 'Development'},
        {'Key': 'BucketType', 'Value': 'AudioStorage'},
        {'Key': 'Security', 'Value': 'SignedURLsOnly'}
    ]
    
    @classmethod
    def audio_bucket_config(cls, bucket_name: str) -> Dict[str, Any]:
        """
        Get complete audio bucket configuration.
        
        Args:
            bucket_name: Name for the S3 bucket
            
        Returns:
            Complete bucket configuration dictionary
        """
        return {
            'name': bucket_name,
            'cors': cls.AUDIO_BUCKET_CORS,
            'lifecycle': cls.AUDIO_BUCKET_LIFECYCLE,
            'encryption': cls.AUDIO_BUCKET_ENCRYPTION,
            'public_access_block': cls.AUDIO_BUCKET_PUBLIC_ACCESS_BLOCK,
            'versioning': cls.AUDIO_BUCKET_VERSIONING,
            'tags': cls.AUDIO_BUCKET_TAGS
        }
    
    @classmethod
    def production_audio_config(cls, bucket_name: str, allowed_origins: list) -> Dict[str, Any]:
        """
        Get production-ready audio bucket configuration.
        
        Args:
            bucket_name: Name for the S3 bucket
            allowed_origins: List of allowed CORS origins for production
            
        Returns:
            Production bucket configuration
        """
        config = cls.audio_bucket_config(bucket_name)
        
        # Override CORS for production
        config['cors']['CORSRules'][0]['AllowedOrigins'] = allowed_origins
        
        # Add production lifecycle rules
        config['lifecycle']['Rules'].extend([
            {
                'ID': 'archive-old-files',
                'Status': 'Enabled',
                'Filter': {'Prefix': ''},
                'Transitions': [
                    {'Days': 30, 'StorageClass': 'STANDARD_IA'},
                    {'Days': 90, 'StorageClass': 'GLACIER'}
                ]
            }
        ])
        
        # Add bucket policy for production security
        config['bucket_policy'] = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'DenyUnencryptedObjectUploads',
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Action': 's3:PutObject',
                    'Resource': f'arn:aws:s3:::{bucket_name}/*',
                    'Condition': {
                        'StringNotEquals': {
                            's3:x-amz-server-side-encryption': 'AES256'
                        }
                    }
                },
                {
                    'Sid': 'DenyPublicReadAccess',
                    'Effect': 'Deny',
                    'Principal': '*',
                    'Action': 's3:GetObject',
                    'Resource': f'arn:aws:s3:::{bucket_name}/*',
                    'Condition': {
                        'StringNotEquals': {
                            'aws:PrincipalArn': 'arn:aws:iam::*:role/VoiceGatewayRole'
                        }
                    }
                }
            ]
        }
        
        # Update tags for production
        config['tags'] = [
            {'Key': 'Project', 'Value': 'VoiceGateway'},
            {'Key': 'Environment', 'Value': 'Production'},
            {'Key': 'BucketType', 'Value': 'AudioStorage'},
            {'Key': 'Security', 'Value': 'SignedURLsOnly'},
            {'Key': 'Compliance', 'Value': 'Required'}
        ]
        
        return config