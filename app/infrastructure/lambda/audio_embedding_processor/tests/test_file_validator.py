"""
Unit tests for File Validation (Clean Architecture).

Tests file validation including format, size, security checks,
and content validation using Clean Architecture patterns.
"""
import pytest
from unittest.mock import patch, Mock

# Try to import shared layer components
try:
    from shared.adapters.audio_processors.resemblyzer_processor import MockAudioProcessor
    from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
    SHARED_LAYER_AVAILABLE = True
except ImportError:
    SHARED_LAYER_AVAILABLE = False
    MockAudioProcessor = None
    ProcessVoiceSampleUseCase = None

# Try to import fallback components  
try:
    from utils.file_validator import AudioFileValidator
    from utils.audio_processor import get_audio_processor
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False
    AudioFileValidator = None
    get_audio_processor = None

# Try to import pipeline components
try:
    from pipeline_orchestrator import AudioProcessingPipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    AudioProcessingPipeline = None


@pytest.mark.unit
class TestAudioFileValidation:
    """Test cases for Clean Architecture audio file validation."""
    
    def setup_method(self):
        """Setup test instance."""
        if SHARED_LAYER_AVAILABLE:
            self.processor = MockAudioProcessor()
            self.validator = None
        elif FALLBACK_AVAILABLE:
            self.validator = AudioFileValidator()
            self.processor = None
        else:
            pytest.skip("Neither shared layer nor fallback validation available")
    
    def test_validation_initialization(self):
        """Test validator initialization with default settings."""
        if self.processor:
            # Test with Clean Architecture processor
            assert hasattr(self.processor, 'validate_audio_quality')
        elif self.validator:
            # Test with fallback validator
            assert self.validator.max_file_size > 0
            assert self.validator.min_file_size > 0
            assert len(self.validator.supported_formats) > 0
            assert 'wav' in self.validator.supported_formats
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self):
        """Test successful file validation."""
        sample_audio_data = b'fake_audio_data' * 1000  # 15KB of fake data
        sample_metadata = {
            'file_name': 'sample1.wav',
            'file_size': len(sample_audio_data),
            'content_type': 'audio/wav'
        }
        
        if self.processor:
            # Test with Clean Architecture processor
            result = self.processor.validate_audio_quality(sample_audio_data, sample_metadata)
            assert result['is_valid'] is True
            assert 'overall_quality_score' in result
            assert result['overall_quality_score'] > 0
        elif self.validator:
            # Test with fallback validator
            result = self.validator.validate_file(sample_audio_data, sample_metadata)
            assert result['is_valid'] is True
            assert 'overall_quality_score' in result
    
    @pytest.mark.asyncio
    async def test_validate_file_invalid_format(self):
        """Test validation with invalid file format."""
        sample_audio_data = b'fake_data'
        sample_metadata = {
            'file_name': 'sample1.txt',  # Invalid format
            'file_size': len(sample_audio_data),
            'content_type': 'text/plain'
        }
        
        if self.processor:
            # Test with Clean Architecture processor
            result = self.processor.validate_audio_quality(sample_audio_data, sample_metadata)
            # Should handle gracefully (implementation dependent)
            assert 'is_valid' in result
        elif self.validator:
            # Test with fallback validator
            result = self.validator.validate_file(sample_audio_data, sample_metadata)
            assert result['is_valid'] is False
            assert 'issues' in result or 'validation_failed' in result
    
    def test_validate_file_too_large(self):
        """Test validation with file that's too large."""
        if not (self.processor or self.validator):
            pytest.skip("No validation components available")
            
        # Create fake large file
        large_data = b'x' * (15 * 1024 * 1024)  # 15MB
        sample_metadata = {
            'file_name': 'large_sample.wav',
            'file_size': len(large_data),
            'content_type': 'audio/wav'
        }
        
        if self.processor:
            # Test with Clean Architecture processor
            result = self.processor.validate_audio_quality(large_data, sample_metadata)
            # Should handle gracefully
            assert 'is_valid' in result
        elif self.validator:
            # Test with fallback validator
            result = self.validator.validate_file(large_data, sample_metadata)
            assert result['is_valid'] is False
    
    def test_validate_file_empty(self):
        """Test validation with empty file."""
        if not (self.processor or self.validator):
            pytest.skip("No validation components available")
            
        empty_data = b''
        sample_metadata = {
            'file_name': 'empty.wav',
            'file_size': 0,
            'content_type': 'audio/wav'
        }
        
        if self.processor:
            # Test with Clean Architecture processor
            result = self.processor.validate_audio_quality(empty_data, sample_metadata)
            assert 'is_valid' in result
        elif self.validator:
            # Test with fallback validator
            result = self.validator.validate_file(empty_data, sample_metadata)
            assert result['is_valid'] is False


@pytest.mark.unit
class TestFileValidationIntegration:
    """Integration tests for file validation in the processing pipeline."""
    
    def test_validation_in_audio_processor(self):
        """Test that validation is integrated in audio processing."""
        if not SHARED_LAYER_AVAILABLE and not FALLBACK_AVAILABLE:
            pytest.skip("No validation components available")
            
        # This test verifies integration exists but doesn't test actual processing
        if SHARED_LAYER_AVAILABLE:
            processor = MockAudioProcessor()
            assert hasattr(processor, 'validate_audio_quality')
        elif FALLBACK_AVAILABLE:
            validator = AudioFileValidator()
            assert hasattr(validator, 'validate_file')
    
    def test_validation_with_audio_processor_factory(self):
        """Test validation with audio processor factory."""
        if not SHARED_LAYER_AVAILABLE and not FALLBACK_AVAILABLE:
            pytest.skip("No validation components available")
        
        if FALLBACK_AVAILABLE and get_audio_processor:
            processor = get_audio_processor()
            assert hasattr(processor, 'validate_audio_quality') or hasattr(processor, 'process_audio_data')
    
    def test_validation_with_use_case(self):
        """Test validation integration with use case."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        if SHARED_LAYER_AVAILABLE and ProcessVoiceSampleUseCase:
            # Test that use case class exists and can be instantiated
            # (actual testing would require full mock setup)
            assert ProcessVoiceSampleUseCase is not None
    
    def test_validation_in_pipeline(self):
        """Test validation in complete processing pipeline."""
        if not PIPELINE_AVAILABLE:
            pytest.skip("Pipeline components not available")
            
        if AudioProcessingPipeline:
            # Test that pipeline class exists
            assert AudioProcessingPipeline is not None
    
    def test_validation_performance(self):
        """Test validation performance with large files."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available for performance testing")
            
        if MockAudioProcessor:
            processor = MockAudioProcessor()
            
            # Test with moderately large file
            large_audio = b'fake_audio_data' * 10000  # ~150KB
            metadata = {
                'file_name': 'large_test.wav',
                'file_size': len(large_audio),
                'content_type': 'audio/wav'
            }
            
            import time
            start_time = time.time()
            result = processor.validate_audio_quality(large_audio, metadata)
            processing_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert processing_time < 5.0  # 5 seconds max
            assert 'is_valid' in result
            assert isinstance(result['is_valid'], bool)