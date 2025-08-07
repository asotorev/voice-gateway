"""
S3 Event parsing and validation for Lambda audio processing.

This module handles parsing AWS S3 events that trigger the Lambda function.
It validates event structure, extracts relevant S3 object information,
and filters events to ensure only valid audio files are processed.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from urllib.parse import unquote_plus

# Lambda environment configuration
try:
    from app.infrastructure.config.infrastructure_settings import infra_settings
except ImportError:
    # Fallback for Lambda environment
    class MockSettings:
        supported_audio_formats = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
        max_audio_file_size_mb = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10'))
        s3_trigger_prefix = os.getenv('S3_TRIGGER_PREFIX', 'audio-uploads/')
        
        @property
        def max_audio_file_size_bytes(self) -> int:
            return self.max_audio_file_size_mb * 1024 * 1024
    
    infra_settings = MockSettings()

logger = logging.getLogger(__name__)


class S3EventParser:
    """
    Parser for S3 events that trigger Lambda functions.
    
    Handles validation and extraction of S3 object information
    from Lambda event payloads.
    """
    
    def __init__(self):
        """Initialize the S3 event parser."""
        self.supported_formats = infra_settings.supported_audio_formats
        self.max_file_size = infra_settings.max_audio_file_size_bytes
        self.trigger_prefix = infra_settings.s3_trigger_prefix
    
    def parse_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Lambda event and extract S3 object information.
        
        Args:
            event: AWS Lambda event payload
            
        Returns:
            List of validated S3 events with object details
            
        Raises:
            ValueError: If event structure is invalid
        """
        try:
            if not event or 'Records' not in event:
                logger.warning("Invalid event structure: missing Records")
                return []
            
            s3_events = []
            
            for record in event['Records']:
                try:
                    s3_event = self._parse_single_record(record)
                    if s3_event and self._validate_s3_event(s3_event):
                        s3_events.append(s3_event)
                        
                except Exception as e:
                    logger.warning("Failed to parse event record", extra={
                        "record": json.dumps(record) if record else None,
                        "error": str(e)
                    })
                    continue
            
            logger.info("Successfully parsed S3 events", extra={
                "total_records": len(event['Records']),
                "valid_events": len(s3_events)
            })
            
            return s3_events
            
        except Exception as e:
            logger.error("Failed to parse Lambda event", extra={
                "event": json.dumps(event) if event else None,
                "error": str(e)
            })
            raise ValueError(f"Invalid event structure: {str(e)}")
    
    def _parse_single_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single event record to extract S3 information.
        
        Args:
            record: Single event record from Lambda event
            
        Returns:
            Dict with S3 object information or None if invalid
        """
        # Validate record structure
        if not record or 'eventSource' not in record:
            logger.debug("Record missing eventSource")
            return None
            
        # Only process S3 events
        if record['eventSource'] != 'aws:s3':
            logger.debug("Non-S3 event ignored", extra={
                "event_source": record.get('eventSource')
            })
            return None
        
        # Extract S3 information
        try:
            s3_info = record['s3']
            bucket_info = s3_info['bucket']
            object_info = s3_info['object']
            
            # URL-decode the object key (handles spaces and special chars)
            object_key = unquote_plus(object_info['key'])
            
            s3_event = {
                'event_name': record.get('eventName', ''),
                'event_time': record.get('eventTime', ''),
                'bucket': bucket_info['name'],
                'key': object_key,
                'size': object_info.get('size', 0),
                'etag': object_info.get('eTag', ''),
                'region': record.get('awsRegion', ''),
                'source_ip': record.get('requestParameters', {}).get('sourceIPAddress', '')
            }
            
            logger.debug("Parsed S3 event", extra=s3_event)
            return s3_event
            
        except KeyError as e:
            logger.warning("Invalid S3 record structure", extra={
                "missing_field": str(e),
                "record": json.dumps(record)
            })
            return None
        except Exception as e:
            logger.error("Unexpected error parsing S3 record", extra={
                "error": str(e),
                "record": json.dumps(record)
            })
            return None
    
    def _validate_s3_event(self, s3_event: Dict[str, Any]) -> bool:
        """
        Validate S3 event for audio processing requirements.
        
        Args:
            s3_event: Parsed S3 event information
            
        Returns:
            True if event is valid for processing
        """
        try:
            # Check if it's an object creation event
            event_name = s3_event.get('event_name', '')
            if not event_name.startswith('ObjectCreated'):
                logger.debug("Not an ObjectCreated event", extra={
                    "event_name": event_name,
                    "key": s3_event.get('key')
                })
                return False
            
            # Validate object key has expected prefix
            object_key = s3_event.get('key', '')
            if not object_key.startswith(self.trigger_prefix):
                logger.debug("Object key does not match trigger prefix", extra={
                    "key": object_key,
                    "expected_prefix": self.trigger_prefix
                })
                return False
            
            # Validate file extension
            if not self._is_supported_audio_format(object_key):
                logger.debug("Unsupported audio format", extra={
                    "key": object_key,
                    "supported_formats": self.supported_formats
                })
                return False
            
            # Validate file size
            file_size = s3_event.get('size', 0)
            if file_size > self.max_file_size:
                logger.warning("File size exceeds maximum limit", extra={
                    "key": object_key,
                    "size_bytes": file_size,
                    "max_size_bytes": self.max_file_size
                })
                return False
            
            # Validate file is not empty
            if file_size == 0:
                logger.warning("Empty file detected", extra={
                    "key": object_key
                })
                return False
            
            # All validations passed
            logger.info("S3 event validation passed", extra={
                "key": object_key,
                "size_bytes": file_size,
                "format": self._get_file_extension(object_key)
            })
            
            return True
            
        except Exception as e:
            logger.error("Error during S3 event validation", extra={
                "s3_event": json.dumps(s3_event) if s3_event else None,
                "error": str(e)
            })
            return False
    
    def _is_supported_audio_format(self, object_key: str) -> bool:
        """
        Check if file has supported audio format extension.
        
        Args:
            object_key: S3 object key
            
        Returns:
            True if format is supported
        """
        extension = self._get_file_extension(object_key)
        return extension.lower() in [fmt.lower() for fmt in self.supported_formats]
    
    def _get_file_extension(self, object_key: str) -> str:
        """
        Extract file extension from object key.
        
        Args:
            object_key: S3 object key
            
        Returns:
            File extension without dot
        """
        if '.' not in object_key:
            return ''
        return object_key.split('.')[-1]
    
    def get_file_info_summary(self, s3_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary information for parsed S3 events.
        
        Args:
            s3_events: List of parsed and validated S3 events
            
        Returns:
            Summary with file counts, sizes, and formats
        """
        if not s3_events:
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'formats': [],
                'buckets': []
            }
        
        total_size = sum(event.get('size', 0) for event in s3_events)
        formats = list(set(self._get_file_extension(event.get('key', '')) 
                          for event in s3_events))
        buckets = list(set(event.get('bucket', '') for event in s3_events))
        
        return {
            'total_files': len(s3_events),
            'total_size_bytes': total_size,
            'formats': formats,
            'buckets': buckets,
            'files': [
                {
                    'key': event.get('key', ''),
                    'size': event.get('size', 0),
                    'format': self._get_file_extension(event.get('key', ''))
                }
                for event in s3_events
            ]
        }
