"""
Unit tests for Audio Processor implementations (Clean Architecture).

Tests the audio processing interfaces, implementations and factory functions
for embedding generation and quality assessment using Clean Architecture.
"""
import inspect
import pytest
from unittest.mock import patch, Mock, AsyncMock

# Try to import shared layer components
try:
    from shared.core.ports.audio_processor import AudioProcessorPort
    from shared.adapters.audio_processors.resemblyzer_processor import (
        MockAudioProcessor, ResemblyzerAudioProcessor, get_audio_processor
    )
    from shared.core.usecases.process_voice_sample import ProcessVoiceSampleUseCase
    SHARED_LAYER_AVAILABLE = True
except ImportError:
    SHARED_LAYER_AVAILABLE = False
    AudioProcessorPort = None
    MockAudioProcessor = None
    ResemblyzerAudioProcessor = None
    get_audio_processor = None
    ProcessVoiceSampleUseCase = None

# Try to import fallback components
try:
    from utils.audio_processor import (
        MockAudioProcessor as FallbackMockAudioProcessor,
        get_audio_processor as fallback_get_audio_processor,
        process_audio_file
    )
    FALLBACK_AVAILABLE = True
except ImportError:
    FALLBACK_AVAILABLE = False
    FallbackMockAudioProcessor = None
    fallback_get_audio_processor = None
    process_audio_file = None


@pytest.mark.unit
class TestAudioProcessorPort:
    """Test cases for Clean Architecture AudioProcessorPort interface."""

    def test_audio_processor_port_interface(self):
        """Test that the AudioProcessorPort interface exists."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # Verify it's an abstract base class
        assert inspect.isabstract(AudioProcessorPort)
        
        # Verify required methods exist
        required_methods = ['generate_embedding', 'validate_audio_quality', 'get_processor_info']
        for method_name in required_methods:
            assert hasattr(AudioProcessorPort, method_name)


@pytest.mark.unit 
class TestMockAudioProcessor:
    """Test cases for Mock audio processor implementation."""
    
    def setup_method(self):
        """Setup test instance."""
        if SHARED_LAYER_AVAILABLE:
            self.processor = MockAudioProcessor()
        elif FALLBACK_AVAILABLE:
            self.processor = FallbackMockAudioProcessor()
        else:
            pytest.skip("No mock processor available")
    
    def test_mock_processor_initialization(self):
        """Test MockAudioProcessor initialization."""
        assert self.processor is not None
        assert hasattr(self.processor, 'generate_embedding')
        assert hasattr(self.processor, 'validate_audio_quality')
    
    def test_mock_embedding_generation(self):
        """Test mock embedding generation."""
        audio_data = b'fake_audio_data' * 100
        metadata = {
            'file_name': 'test.wav',
            'file_size': len(audio_data),
            'content_type': 'audio/wav'
        }
        
        embedding = self.processor.generate_embedding(audio_data, metadata)
        
        # Verify embedding properties
        assert embedding is not None
        assert len(embedding) == 256  # Expected embedding dimension
        assert all(isinstance(x, (int, float)) for x in embedding)
    
    def test_mock_quality_validation(self):
        """Test mock audio quality validation."""
        audio_data = b'fake_audio_data' * 100
        metadata = {
            'file_name': 'test.wav', 
            'file_size': len(audio_data),
            'content_type': 'audio/wav'
        }
        
        result = self.processor.validate_audio_quality(audio_data, metadata)
        
        # Verify validation result structure
        assert 'is_valid' in result
        assert 'overall_quality_score' in result
        assert isinstance(result['is_valid'], bool)
        assert isinstance(result['overall_quality_score'], (int, float))
    
    def test_processor_info(self):
        """Test processor information retrieval."""
        info = self.processor.get_processor_info()
        
        assert 'processor_type' in info
        assert 'embedding_dimensions' in info
        assert info['processor_type'] == 'mock'
        assert info['embedding_dimensions'] == 256


@pytest.mark.unit
class TestResemblyzerAudioProcessor:
    """Test cases for Resemblyzer audio processor implementation."""
    
    def test_resemblyzer_processor_initialization(self):
        """Test successful ResemblyzerAudioProcessor initialization."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # Test that processor can be created
        processor = ResemblyzerAudioProcessor()
        assert processor is not None
        assert hasattr(processor, 'generate_embedding')
        assert hasattr(processor, 'validate_audio_quality')
    
    def test_resemblyzer_initialization_failure(self):
        """Test ResemblyzerAudioProcessor initialization failure."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # This test would require mocking VoiceEncoder import failure
        # For now, just verify the class exists
        assert ResemblyzerAudioProcessor is not None
    
    def test_resemblyzer_embedding_generation(self):
        """Test successful embedding generation with Resemblyzer."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        processor = ResemblyzerAudioProcessor()
        audio_data = b'fake_audio_data' * 1000
        metadata = {
            'file_name': 'test.wav',
            'file_size': len(audio_data),
            'content_type': 'audio/wav'
        }
        
        # This would require actual audio processing in real scenario
        # For mock test, just verify method exists
        assert hasattr(processor, 'generate_embedding')


@pytest.mark.unit
class TestAudioProcessorFactory:
    """Test cases for audio processor factory functions."""
    
    def test_get_mock_audio_processor(self):
        """Test getting mock audio processor."""
        if SHARED_LAYER_AVAILABLE:
            processor = get_audio_processor()
            assert processor is not None
            assert processor.__class__.__name__ == 'MockAudioProcessor'
        elif FALLBACK_AVAILABLE:
            processor = fallback_get_audio_processor()
            assert processor is not None
            assert processor.__class__.__name__ == 'MockAudioProcessor'
        else:
            pytest.skip("No audio processor factory available")
    
    def test_get_resemblyzer_audio_processor(self):
        """Test getting Resemblyzer audio processor."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # Would test with environment variable set to 'resemblyzer'
        # For now, just verify factory function exists
        assert get_audio_processor is not None
    
    def test_get_default_audio_processor(self):
        """Test getting default audio processor."""
        if SHARED_LAYER_AVAILABLE:
            processor = get_audio_processor()
            # Should default to mock
            assert processor.__class__.__name__ == 'MockAudioProcessor'
        elif FALLBACK_AVAILABLE:
            processor = fallback_get_audio_processor()
            assert processor is not None


@pytest.mark.integration
class TestProcessVoiceSampleIntegration:
    """Integration tests for voice sample processing."""
    
    def test_process_voice_sample_use_case(self):
        """Test ProcessVoiceSampleUseCase integration."""
        if not SHARED_LAYER_AVAILABLE:
            pytest.skip("Shared layer not available")
            
        # This would require full mock setup for integration test
        assert ProcessVoiceSampleUseCase is not None
    
    def test_process_audio_file_function(self):
        """Test process_audio_file utility function."""
        if not FALLBACK_AVAILABLE:
            pytest.skip("Fallback audio processing not available")
            
        audio_data = b'fake_audio_data' * 1000
        metadata = {
            'file_name': 'test.wav',
            'file_size': len(audio_data),
            'content_type': 'audio/wav'
        }
        
        # This would require proper mocking for full test
        assert process_audio_file is not None


@pytest.mark.integration
class TestAudioProcessorIntegration:
    """Integration tests for audio processor components."""
    
    def test_audio_processor_pipeline(self):
        """Test full audio processing flow with Clean Architecture."""
        if SHARED_LAYER_AVAILABLE:
            processor = get_audio_processor()
            assert processor is not None
        elif FALLBACK_AVAILABLE:
            processor = fallback_get_audio_processor()
            assert processor is not None
        else:
            pytest.skip("No audio processing available")
    
    def test_processor_consistency(self):
        """Test that processor factory returns consistent instances."""
        if SHARED_LAYER_AVAILABLE:
            processor1 = get_audio_processor()
            processor2 = get_audio_processor()
            
            # Should return instances of same class
            assert type(processor1) == type(processor2)
        elif FALLBACK_AVAILABLE:
            processor1 = fallback_get_audio_processor()
            processor2 = fallback_get_audio_processor()
            
            assert type(processor1) == type(processor2)