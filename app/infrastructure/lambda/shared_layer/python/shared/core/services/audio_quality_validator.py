"""
Audio Quality Validation Service.

Provides comprehensive audio file validation including format checking,
quality assessment, security validation, and content analysis for voice
audio samples in the voice authentication system.

This service is part of the shared layer and can be used by multiple
Lambda functions for consistent audio validation.
"""
import os
import logging
import threading
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AudioQualityValidationConfig:
    """Configuration for audio quality validation."""
    
    def __init__(self):
        self.max_file_size = int(os.getenv('MAX_AUDIO_FILE_SIZE_MB', '10')) * 1024 * 1024  # 10MB default
        self.min_file_size = int(os.getenv('MIN_AUDIO_FILE_SIZE_BYTES', '1024'))  # 1KB minimum
        self.supported_formats = os.getenv('SUPPORTED_AUDIO_FORMATS', 'wav,mp3,m4a,flac').split(',')
        self.max_duration_seconds = float(os.getenv('MAX_AUDIO_DURATION_SECONDS', '30.0'))
        self.min_duration_seconds = float(os.getenv('MIN_AUDIO_DURATION_SECONDS', '1.0'))
        self.quality_threshold = float(os.getenv('AUDIO_QUALITY_THRESHOLD', '0.7'))
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'max_file_size_bytes': self.max_file_size,
            'min_file_size_bytes': self.min_file_size,
            'supported_formats': self.supported_formats,
            'max_duration_seconds': self.max_duration_seconds,
            'min_duration_seconds': self.min_duration_seconds,
            'quality_threshold': self.quality_threshold
        }


class AudioQualityValidator:
    """
    Comprehensive audio quality validation service.
    
    Validates audio files for format, size, duration, quality, and security
    requirements for voice authentication processing.
    """
    
    def __init__(self, config: Optional[AudioQualityValidationConfig] = None):
        """Initialize the audio quality validator."""
        self.config = config or AudioQualityValidationConfig()
        self._lock = threading.Lock()
        logger.info("Audio quality validator initialized", extra=self.config.to_dict())
    
    def validate_file(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive audio file validation.
        
        Args:
            audio_data: Raw audio file data
            metadata: File metadata including name, size, content_type
            
        Returns:
            Dict with validation results including:
            - is_valid: bool
            - validation_passed: List[str] 
            - validation_failed: List[str]
            - warnings: List[str]
            - overall_score: float
            - validated_at: str
        """
        with self._lock:
            logger.debug("Starting audio file validation", extra={
                "file_name": metadata.get('file_name', 'unknown'),
                "file_size": len(audio_data),
                "content_type": metadata.get('content_type', 'unknown')
            })
            
            validation_result = {
                'is_valid': True,
                'validation_passed': [],
                'validation_failed': [],
                'warnings': [],
                'overall_score': 1.0,
                'validated_at': datetime.now(timezone.utc).isoformat(),
                'validation_details': {}
            }
            
            # Perform validation checks
            self._validate_file_size(audio_data, metadata, validation_result)
            self._validate_file_format(audio_data, metadata, validation_result)
            self._validate_content_type(metadata, validation_result)
            self._validate_security(audio_data, metadata, validation_result)
            self._validate_metadata_consistency(audio_data, metadata, validation_result)
            
            # Calculate overall validation score
            self._calculate_overall_score(validation_result)
            
            # Determine final validation status
            validation_result['is_valid'] = (
                len(validation_result['validation_failed']) == 0 and
                validation_result['overall_score'] >= self.config.quality_threshold
            )
            
            logger.info("Audio file validation completed", extra={
                "file_name": metadata.get('file_name', 'unknown'),
                "is_valid": validation_result['is_valid'],
                "overall_score": validation_result['overall_score'],
                "failed_checks": len(validation_result['validation_failed'])
            })
            
            return validation_result
    
    def _validate_file_size(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate file size constraints."""
        file_size = len(audio_data)
        
        if file_size == 0:
            result['validation_failed'].append("File is empty")
            return
        
        if file_size < self.config.min_file_size:
            result['validation_failed'].append(f"File too small: {file_size} bytes (minimum: {self.config.min_file_size})")
        else:
            result['validation_passed'].append("File size minimum check")
        
        if file_size > self.config.max_file_size:
            result['validation_failed'].append(f"File too large: {file_size} bytes (maximum: {self.config.max_file_size})")
        else:
            result['validation_passed'].append("File size maximum check")
        
        # Check metadata consistency
        declared_size = metadata.get('file_size', file_size)
        if abs(declared_size - file_size) > 1024:  # Allow 1KB tolerance
            result['warnings'].append(f"File size mismatch: declared {declared_size}, actual {file_size}")
    
    def _validate_file_format(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate file format based on extension and content."""
        file_name = metadata.get('file_name', '')
        
        if not file_name:
            result['validation_failed'].append("No file name provided")
            return
        
        # Extract file extension
        file_extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        if not file_extension:
            result['validation_failed'].append("No file extension found")
            return
        
        if file_extension not in self.config.supported_formats:
            result['validation_failed'].append(f"Unsupported format: {file_extension} (supported: {', '.join(self.config.supported_formats)})")
        else:
            result['validation_passed'].append(f"File format check: {file_extension}")
        
        # Basic content validation
        self._validate_file_content_signature(audio_data, file_extension, result)
    
    def _validate_content_type(self, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate HTTP content type."""
        content_type = metadata.get('content_type', '').lower()
        
        if not content_type:
            result['warnings'].append("No content type specified")
            return
        
        valid_content_types = [
            'audio/wav', 'audio/wave', 'audio/x-wav',
            'audio/mpeg', 'audio/mp3',
            'audio/mp4', 'audio/m4a',
            'audio/flac', 'audio/x-flac'
        ]
        
        if content_type not in valid_content_types:
            result['warnings'].append(f"Unusual content type: {content_type}")
        else:
            result['validation_passed'].append(f"Content type check: {content_type}")
    
    def _validate_file_content_signature(self, audio_data: bytes, file_extension: str, result: Dict[str, Any]) -> None:
        """Validate file content matches expected format signature."""
        if len(audio_data) < 12:
            result['validation_failed'].append("File too short for format validation")
            return
        
        # Check common audio file signatures
        header = audio_data[:12]
        
        format_signatures = {
            'wav': [b'RIFF', b'WAVE'],
            'mp3': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
            'flac': [b'fLaC'],
            'm4a': [b'ftypM4A']
        }
        
        if file_extension in format_signatures:
            signatures = format_signatures[file_extension]
            signature_found = any(
                header.startswith(sig) or sig in header 
                for sig in signatures
            )
            
            if signature_found:
                result['validation_passed'].append(f"File signature validation: {file_extension}")
            else:
                result['warnings'].append(f"File signature mismatch for {file_extension} format")
    
    def _validate_security(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Perform basic security validation."""
        # Check for suspicious patterns
        if len(audio_data) > 0:
            # Look for embedded executable signatures
            suspicious_patterns = [
                b'MZ',  # PE executable
                b'\x7fELF',  # ELF executable
                b'\xca\xfe\xba\xbe',  # Mach-O
                b'#!/bin/',  # Script shebang
                b'<script',  # HTML script
                b'javascript:',  # Javascript
            ]
            
            for pattern in suspicious_patterns:
                if pattern in audio_data[:1024]:  # Check first 1KB
                    result['validation_failed'].append(f"Suspicious content pattern detected")
                    break
            else:
                result['validation_passed'].append("Security pattern check")
        
        # File name security check
        file_name = metadata.get('file_name', '')
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.js', '.vbs', '.ps1']
        
        if any(file_name.lower().endswith(ext) for ext in suspicious_extensions):
            result['validation_failed'].append("Suspicious file extension detected")
        else:
            result['validation_passed'].append("File extension security check")
    
    def _validate_metadata_consistency(self, audio_data: bytes, metadata: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Validate metadata consistency."""
        file_name = metadata.get('file_name', '')
        content_type = metadata.get('content_type', '')
        
        # Check file extension vs content type consistency
        if file_name and content_type:
            extension = file_name.lower().split('.')[-1] if '.' in file_name else ''
            
            extension_content_map = {
                'wav': ['audio/wav', 'audio/wave', 'audio/x-wav'],
                'mp3': ['audio/mpeg', 'audio/mp3'],
                'm4a': ['audio/mp4', 'audio/m4a'],
                'flac': ['audio/flac', 'audio/x-flac']
            }
            
            if extension in extension_content_map:
                expected_types = extension_content_map[extension]
                if content_type.lower() not in expected_types:
                    result['warnings'].append(f"Content type '{content_type}' doesn't match extension '{extension}'")
                else:
                    result['validation_passed'].append("Extension/content-type consistency")
    
    def _calculate_overall_score(self, result: Dict[str, Any]) -> None:
        """Calculate overall validation score."""
        passed_count = len(result['validation_passed'])
        failed_count = len(result['validation_failed'])
        warning_count = len(result['warnings'])
        
        if passed_count + failed_count == 0:
            result['overall_score'] = 0.0
            return
        
        # Base score from pass/fail ratio
        base_score = passed_count / (passed_count + failed_count) if (passed_count + failed_count) > 0 else 0.0
        
        # Penalty for warnings (reduce score by 5% per warning)
        warning_penalty = min(0.5, warning_count * 0.05)
        
        # Final score
        result['overall_score'] = max(0.0, base_score - warning_penalty)
        
        result['validation_details'] = {
            'passed_checks': passed_count,
            'failed_checks': failed_count,
            'warnings': warning_count,
            'base_score': base_score,
            'warning_penalty': warning_penalty
        }


# Global instance for easy access
audio_quality_validator = AudioQualityValidator()


def validate_audio_quality(audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function for audio quality validation.
    
    Args:
        audio_data: Raw audio file data
        metadata: File metadata
        
    Returns:
        Validation result dictionary
    """
    return audio_quality_validator.validate_file(audio_data, metadata)
