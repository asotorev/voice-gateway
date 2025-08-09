"""
Audio file validation for Lambda processing pipeline.

This module provides comprehensive validation for audio files before processing,
including format validation, content analysis, and security checks to ensure
only valid audio files are processed by the embedding generation pipeline.
"""
import os
import logging
import tempfile
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AudioFileValidator:
    """
    Comprehensive audio file validator for Lambda processing.
    
    Validates audio files for format, size, content, and security
    before allowing them to proceed through the embedding pipeline.
    """
    
    def __init__(self):
        """Initialize audio file validator with configuration."""
        # Load configuration from environment
        self.max_file_size = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10')) * 1024 * 1024
        self.min_file_size = 1000  # 1KB minimum
        self.supported_formats = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
        self.max_duration_seconds = int(os.getenv('MAX_AUDIO_DURATION_SECONDS', '300'))  # 5 minutes
        self.min_duration_seconds = int(os.getenv('MIN_AUDIO_DURATION_SECONDS', '1'))  # 1 second
        
        logger.info("Audio file validator initialized", extra={
            "max_file_size_mb": self.max_file_size // (1024 * 1024),
            "supported_formats": self.supported_formats,
            "max_duration_seconds": self.max_duration_seconds
        })
    
    def validate_file(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive validation of audio file.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: File metadata including name, size, etc.
            
        Returns:
            Dict with validation results and detailed analysis
        """
        logger.info("Starting comprehensive file validation", extra={
            "file_name": metadata.get('file_name', 'unknown'),
            "file_size_bytes": len(audio_data)
        })
        
        validation_result = {
            'is_valid': True,
            'validation_passed': [],
            'validation_failed': [],
            'warnings': [],
            'file_info': {},
            'security_checks': {},
            'content_analysis': {},
            'validated_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Basic file validations
            self._validate_file_size(audio_data, validation_result)
            self._validate_file_format(metadata, validation_result)
            self._validate_file_extension(metadata, validation_result)
            
            # Content validations
            self._validate_file_headers(audio_data, metadata, validation_result)
            self._validate_file_content(audio_data, validation_result)
            
            # Security validations
            self._perform_security_checks(audio_data, metadata, validation_result)
            
            # Audio-specific validations (basic)
            self._validate_audio_properties(audio_data, metadata, validation_result)
            
            # Determine overall validation result
            validation_result['is_valid'] = len(validation_result['validation_failed']) == 0
            
            logger.info("File validation completed", extra={
                "is_valid": validation_result['is_valid'],
                "passed_checks": len(validation_result['validation_passed']),
                "failed_checks": len(validation_result['validation_failed']),
                "warnings": len(validation_result['warnings'])
            })
            
            return validation_result
            
        except Exception as e:
            logger.error("File validation failed with exception", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "file_name": metadata.get('file_name', 'unknown')
            })
            
            validation_result['is_valid'] = False
            validation_result['validation_failed'].append(f"Validation exception: {str(e)}")
            validation_result['error_details'] = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'recoverable': self._is_recoverable_error(e)
            }
            return validation_result
    
    def _validate_file_size(self, audio_data: bytes, result: Dict[str, Any]) -> None:
        """Validate file size constraints."""
        file_size = len(audio_data)
        
        if file_size == 0:
            result['validation_failed'].append("File is empty")
        elif file_size < self.min_file_size:
            result['validation_failed'].append(f"File too small: {file_size} bytes (minimum: {self.min_file_size})")
        elif file_size > self.max_file_size:
            result['validation_failed'].append(f"File too large: {file_size} bytes (maximum: {self.max_file_size})")
        else:
            result['validation_passed'].append("File size validation")
        
        result['file_info']['size_bytes'] = file_size
        result['file_info']['size_mb'] = round(file_size / (1024 * 1024), 2)
    
    def _validate_file_format(self, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate file format against supported formats."""
        file_extension = self._get_file_extension(metadata.get('file_name', ''))
        
        if not file_extension:
            result['validation_failed'].append("No file extension found")
        elif file_extension.lower() not in [fmt.lower() for fmt in self.supported_formats]:
            result['validation_failed'].append(f"Unsupported format: {file_extension}")
        else:
            result['validation_passed'].append("File format validation")
        
        result['file_info']['extension'] = file_extension
        result['file_info']['format_supported'] = file_extension.lower() in [fmt.lower() for fmt in self.supported_formats]
    
    def _validate_file_extension(self, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate file extension matches content type if available."""
        file_extension = self._get_file_extension(metadata.get('file_name', ''))
        content_type = metadata.get('content_type', '')
        
        # Expected content type mappings
        extension_content_types = {
            'wav': ['audio/wav', 'audio/wave', 'audio/x-wav'],
            'mp3': ['audio/mpeg', 'audio/mp3'],
            'm4a': ['audio/mp4', 'audio/m4a', 'audio/x-m4a'],
            'flac': ['audio/flac', 'audio/x-flac']
        }
        
        if content_type and file_extension:
            expected_types = extension_content_types.get(file_extension.lower(), [])
            if expected_types and content_type not in expected_types and not content_type.startswith('audio/'):
                result['warnings'].append(f"Content type '{content_type}' doesn't match extension '{file_extension}'")
            else:
                result['validation_passed'].append("Extension-content type validation")
    
    def _validate_file_headers(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate file headers match expected audio formats."""
        if len(audio_data) < 12:  # Need at least 12 bytes for header checks
            result['validation_failed'].append("File too small for header validation")
            return
        
        header = audio_data[:12]
        file_extension = self._get_file_extension(metadata.get('file_name', '')).lower()
        
        # Common audio file signatures
        audio_signatures = {
            'wav': [b'RIFF', b'WAVE'],
            'mp3': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
            'flac': [b'fLaC'],
            'm4a': [b'ftypM4A', b'ftypisom', b'ftypmp42']
        }
        
        if file_extension in audio_signatures:
            signatures = audio_signatures[file_extension]
            header_match = any(header.startswith(sig) or sig in header for sig in signatures)
            
            if header_match:
                result['validation_passed'].append("File header validation")
            else:
                result['validation_failed'].append(f"File header doesn't match expected {file_extension} format")
        else:
            result['warnings'].append(f"No header validation available for {file_extension} format")
        
        result['file_info']['header_hex'] = header.hex()[:24]  # First 12 bytes as hex
    
    def _validate_file_content(self, audio_data: bytes, result: Dict[str, Any]) -> None:
        """Perform basic content validation."""
        # If file is empty, avoid further calculations that may divide by zero
        if len(audio_data) == 0:
            result['content_analysis']['null_byte_percentage'] = 0.0
            result['warnings'].append("Empty audio content")
            return

        # Check for suspiciously uniform data (could indicate corruption or not audio)
        if len(audio_data) > 1000:
            sample = audio_data[:1000]
            unique_bytes = len(set(sample))
            
            if unique_bytes < 10:  # Very low entropy
                result['warnings'].append("File has very low entropy - may be corrupted")
            elif unique_bytes > 250:  # Good entropy
                result['validation_passed'].append("Content entropy validation")
        
        # Check for null bytes (shouldn't be too many in audio files)
        null_count = audio_data.count(b'\x00')
        null_percentage = (null_count / len(audio_data)) * 100
        
        if null_percentage > 50:
            result['warnings'].append(f"High percentage of null bytes: {null_percentage:.1f}%")
        
        result['content_analysis']['null_byte_percentage'] = round(null_percentage, 2)
        result['content_analysis']['entropy_score'] = unique_bytes if len(audio_data) > 1000 else None
    
    def _perform_security_checks(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Perform security-related validations."""
        security_result = {
            'malicious_patterns': [],
            'suspicious_characteristics': [],
            'security_score': 100  # Start with perfect score
        }
        
        # Check for executable signatures in audio data
        executable_signatures = [
            b'MZ',  # Windows PE
            b'\x7fELF',  # Linux ELF
            b'\xfe\xed\xfa',  # macOS Mach-O
        ]
        
        for sig in executable_signatures:
            if sig in audio_data[:1024]:  # Check first 1KB
                security_result['malicious_patterns'].append(f"Executable signature found: {sig.hex()}")
                security_result['security_score'] -= 50
        
        # Check for script tags or suspicious patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'eval(',
            b'document.',
            b'window.'
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in audio_data[:2048].lower():  # Check first 2KB
                security_result['suspicious_characteristics'].append(f"Script pattern found: {pattern.decode('ascii', errors='ignore')}")
                security_result['security_score'] -= 20
        
        # Check file name for suspicious characteristics
        file_name = metadata.get('file_name', '')
        if len(file_name) > 255:
            security_result['suspicious_characteristics'].append("Unusually long filename")
            security_result['security_score'] -= 10
        
        # Check for double extensions
        if file_name.count('.') > 1:
            security_result['suspicious_characteristics'].append("Multiple file extensions")
            security_result['security_score'] -= 15
        
        result['security_checks'] = security_result
        
        if security_result['malicious_patterns'] or security_result['suspicious_characteristics']:
            result['validation_failed'].append("Security validation failed - malicious patterns detected")
        elif security_result['security_score'] < 70:
            result['warnings'].append(f"Low security score: {security_result['security_score']}")
        else:
            result['validation_passed'].append("Security validation")
    
    def _validate_audio_properties(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate basic audio properties (without external libraries)."""
        # This is a basic implementation without audio libraries
        # For production, you might want to use libraries like librosa or pydub
        
        file_extension = self._get_file_extension(metadata.get('file_name', '')).lower()
        
        # Basic WAV file analysis
        if file_extension == 'wav' and len(audio_data) > 44:
            try:
                # Parse basic WAV header
                if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
                    # Extract basic info from WAV header
                    channels = int.from_bytes(audio_data[22:24], 'little')
                    sample_rate = int.from_bytes(audio_data[24:28], 'little')
                    bits_per_sample = int.from_bytes(audio_data[34:36], 'little')
                    
                    # Validate common audio parameters
                    if channels not in [1, 2]:
                        result['warnings'].append(f"Unusual channel count: {channels}")
                    
                    if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
                        result['warnings'].append(f"Unusual sample rate: {sample_rate} Hz")
                    
                    if bits_per_sample not in [8, 16, 24, 32]:
                        result['warnings'].append(f"Unusual bit depth: {bits_per_sample}")
                    
                    result['content_analysis']['audio_properties'] = {
                        'format': 'wav',
                        'channels': channels,
                        'sample_rate': sample_rate,
                        'bits_per_sample': bits_per_sample
                    }
                    
                    result['validation_passed'].append("Basic audio properties validation")
                else:
                    result['warnings'].append("Invalid WAV header structure")
            except Exception as e:
                result['warnings'].append(f"Could not parse WAV header: {str(e)}")
        else:
            # For non-WAV files, just note that we can't analyze properties
            result['content_analysis']['audio_properties'] = {
                'format': file_extension,
                'analysis': 'basic_validation_only'
            }
    
    def _get_file_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if '.' not in filename:
            return ''
        return filename.split('.')[-1]
    
    def quick_validate(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """
        Perform quick validation for basic checks.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: File metadata
            
        Returns:
            True if file passes basic validation
        """
        # Quick size check
        if len(audio_data) == 0 or len(audio_data) > self.max_file_size:
            return False
        
        # Quick format check
        file_extension = self._get_file_extension(metadata.get('file_name', ''))
        if file_extension.lower() not in [fmt.lower() for fmt in self.supported_formats]:
            return False
        
        # Quick security check - no executable signatures
        if b'MZ' in audio_data[:100] or b'\x7fELF' in audio_data[:100]:
            return False
        
        return True
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate human-readable validation summary.
        
        Args:
            validation_result: Result from validate_file()
            
        Returns:
            Summary string
        """
        if validation_result['is_valid']:
            return f"Valid - {len(validation_result['validation_passed'])} checks passed"
        else:
            failed_count = len(validation_result['validation_failed'])
            return f"Invalid - {failed_count} check(s) failed: {', '.join(validation_result['validation_failed'][:2])}"
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """
        Determine if an error is recoverable.
        
        Args:
            error: Exception that occurred during validation
            
        Returns:
            True if error might be recoverable with retry
        """
        recoverable_errors = (
            IOError,
            OSError,
            MemoryError,
            TimeoutError
        )
        
        # Network-related errors that might be transient
        if "timeout" in str(error).lower() or "connection" in str(error).lower():
            return True
            
        return isinstance(error, recoverable_errors)
    
    def validate_with_retry(self, audio_data: bytes, metadata: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """
        Validate file with retry logic for recoverable errors.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: File metadata
            max_retries: Maximum number of retry attempts
            
        Returns:
            Validation result with retry information
        """
        for attempt in range(max_retries + 1):
            try:
                result = self.validate_file(audio_data, metadata)
                
                if result['is_valid'] or not result.get('error_details', {}).get('recoverable', False):
                    # Success or non-recoverable error - don't retry
                    if attempt > 0:
                        result['retry_info'] = {
                            'attempts': attempt + 1,
                            'succeeded_on_retry': True
                        }
                    return result
                    
            except Exception as e:
                if attempt == max_retries or not self._is_recoverable_error(e):
                    # Final attempt or non-recoverable error
                    logger.error("Validation failed after retries", extra={
                        "attempts": attempt + 1,
                        "error": str(e),
                        "file_name": metadata.get('file_name', 'unknown')
                    })
                    
                    return {
                        'is_valid': False,
                        'validation_passed': [],
                        'validation_failed': [f"Validation failed after {attempt + 1} attempts: {str(e)}"],
                        'warnings': [],
                        'error_details': {
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'recoverable': self._is_recoverable_error(e)
                        },
                        'retry_info': {
                            'attempts': attempt + 1,
                            'max_retries': max_retries,
                            'succeeded_on_retry': False
                        }
                    }
                else:
                    # Recoverable error - log and retry
                    logger.warning("Validation failed, retrying", extra={
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "error": str(e),
                        "file_name": metadata.get('file_name', 'unknown')
                    })
                    
                    # Brief delay before retry (exponential backoff)
                    time.sleep(0.1 * (2 ** attempt))
        
        # Should not reach here, but safety fallback
        return {
            'is_valid': False,
            'validation_failed': ['Validation failed after all retry attempts'],
            'retry_info': {'attempts': max_retries + 1, 'succeeded_on_retry': False}
        }
    
    def create_validation_error(self, error_message: str, error_type: str = "ValidationError", recoverable: bool = False) -> Dict[str, Any]:
        """
        Create standardized validation error response.
        
        Args:
            error_message: Human-readable error message
            error_type: Type of error (for categorization)
            recoverable: Whether error might be recoverable
            
        Returns:
            Standardized error response
        """
        return {
            'is_valid': False,
            'validation_passed': [],
            'validation_failed': [error_message],
            'warnings': [],
            'error_details': {
                'error_type': error_type,
                'error_message': error_message,
                'recoverable': recoverable
            },
            'validated_at': datetime.now(timezone.utc).isoformat()
        }


# Global validator instance
audio_file_validator = AudioFileValidator()
