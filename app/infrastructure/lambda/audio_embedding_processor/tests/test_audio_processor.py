"""
Unit tests for AudioProcessor implementations.

Tests the audio processing interface and mock implementation
for embedding generation and quality assessment.
"""
import pytest
from unittest.mock import patch, Mock
from utils.audio_processor import (
    MockAudioProcessor, 
    ResemblyzerAudioProcessor,
    get_audio_processor,
    process_audio_file
)
from .conftest import create_mock_getenv


@pytest.mark.unit
class TestMockAudioProcessor:
    """Test cases for MockAudioProcessor."""
    
    def setup_method(self):
        """Setup test instance."""
        self.processor = MockAudioProcessor()
    
    def test_initialization(self):
        """Test MockAudioProcessor initialization."""
        processor = MockAudioProcessor()
        
        assert processor.embedding_dimensions == 256
        assert processor.processor_version == "mock-1.0.0"
    
    def test_generate_embedding_success(self, sample_audio_data, sample_file_metadata):
        """Test successful embedding generation."""
        embedding = self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 256
        assert all(isinstance(x, float) for x in embedding)
        assert all(-1.0 <= x <= 1.0 for x in embedding)
    
    def test_generate_embedding_empty_data(self, sample_file_metadata):
        """Test embedding generation with empty audio data."""
        with pytest.raises(RuntimeError, match="Mock embedding generation failed: Audio data is empty"):
            self.processor.generate_embedding(b'', sample_file_metadata)
    
    def test_generate_embedding_deterministic(self, sample_audio_data, sample_file_metadata):
        """Test that embedding generation is deterministic."""
        embedding1 = self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
        embedding2 = self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
        
        assert embedding1 == embedding2
    
    def test_generate_embedding_different_inputs(self, sample_file_metadata):
        """Test that different inputs produce different embeddings."""
        data1 = b'audio_data_1' + b'\x00' * 1000
        data2 = b'audio_data_2' + b'\x00' * 1000
        
        embedding1 = self.processor.generate_embedding(data1, sample_file_metadata)
        embedding2 = self.processor.generate_embedding(data2, sample_file_metadata)
        
        assert embedding1 != embedding2
    
    def test_validate_audio_quality_success(self, sample_audio_data, sample_file_metadata):
        """Test successful audio quality validation."""
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        assert isinstance(result, dict)
        assert 'overall_quality_score' in result
        assert 'snr_estimate' in result
        assert 'voice_activity_ratio' in result
        assert 'background_noise_level' in result
        assert 'quality_issues' in result
        
        # Check value ranges
        assert 0.0 <= result['overall_quality_score'] <= 1.0
        assert result['snr_estimate'] >= 0.0
        assert 0.0 <= result['voice_activity_ratio'] <= 1.0
        assert 0.0 <= result['background_noise_level'] <= 1.0
    
    def test_validate_audio_quality_empty_data(self, sample_file_metadata):
        """Test quality validation with empty audio data."""
        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            self.processor.validate_audio_quality(b'', sample_file_metadata)
    
    def test_validate_audio_quality_small_file(self, sample_file_metadata):
        """Test quality validation with very small file."""
        small_data = b'x' * 100  # Very small file
        
        result = self.processor.validate_audio_quality(small_data, sample_file_metadata)
        
        # Should work but with lower quality scores
        assert result['overall_quality_score'] < 0.8
        assert 'File very small' in result['quality_issues']
    
    def test_get_processor_info(self):
        """Test processor info retrieval."""
        info = self.processor.get_processor_info()
        
        assert info['processor_type'] == 'mock'
        assert info['processor_name'] == 'MockAudioProcessor'
        assert info['processor_version'] == 'mock-1.0.0'
        assert info['embedding_dimensions'] == 256
        assert 'capabilities' in info
        assert 'limitations' in info


@pytest.mark.unit
class TestResemblyzerAudioProcessor:
    """Test cases for ResemblyzerAudioProcessor (currently falls back to mock)."""
    
    def setup_method(self):
        """Setup test instance."""
        self.processor = ResemblyzerAudioProcessor()
    
    def test_initialization(self):
        """Test ResemblyzerAudioProcessor initialization."""
        processor = ResemblyzerAudioProcessor()
        
        assert processor.processor_version == "resemblyzer-1.0.0"
    
    def test_generate_embedding_fallback_to_mock(self, sample_audio_data, sample_file_metadata):
        """Test that embedding generation works with Resemblyzer."""
        embedding = self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
        
        # Should return embedding from Resemblyzer
        assert isinstance(embedding, list)
        assert len(embedding) == 256
    
    def test_validate_audio_quality_fallback_to_mock(self, sample_audio_data, sample_file_metadata):
        """Test that quality validation works with Resemblyzer."""
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        # Should return quality assessment from Resemblyzer
        assert isinstance(result, dict)
        assert 'overall_quality_score' in result
    
    def test_get_processor_info(self):
        """Test processor info for Resemblyzer."""
        info = self.processor.get_processor_info()
        
        assert info['processor_type'] == 'resemblyzer'
        assert info['processor_name'] == 'ResemblyzerAudioProcessor'
        assert info['status'] == 'active'


@pytest.mark.unit
class TestGetAudioProcessor:
    """Test cases for audio processor factory function."""
    
    def test_get_audio_processor_mock(self):
        """Test getting mock audio processor."""
        with patch('os.getenv', side_effect=create_mock_getenv('mock', '256')):
            processor = get_audio_processor()
            
            assert isinstance(processor, MockAudioProcessor)
    
    def test_get_audio_processor_resemblyzer(self):
        """Test getting Resemblyzer processor (falls back to mock)."""
        with patch('os.getenv', side_effect=create_mock_getenv('resemblyzer', '256')):
            processor = get_audio_processor()
            
            # Currently returns ResemblyzerAudioProcessor which falls back to mock
            assert isinstance(processor, ResemblyzerAudioProcessor)
    
    def test_get_audio_processor_default(self):
        """Test getting default processor."""
        with patch('os.getenv', side_effect=create_mock_getenv('', '256')):
            processor = get_audio_processor()
            
            assert isinstance(processor, MockAudioProcessor)
    
    def test_get_audio_processor_invalid_type(self):
        """Test getting processor with invalid type."""
        with patch('os.getenv', side_effect=create_mock_getenv('invalid_type', '256')):
            processor = get_audio_processor()
            
            # Should default to mock
            assert isinstance(processor, MockAudioProcessor)


@pytest.mark.unit
class TestProcessAudioFile:
    """Test cases for process_audio_file function."""
    
    def test_process_audio_file_success(self, sample_audio_data, sample_file_metadata):
        """Test successful audio file processing."""
        result = process_audio_file(sample_audio_data, sample_file_metadata)
        
        assert isinstance(result, dict)
        assert 'embedding' in result
        assert 'quality_assessment' in result
        assert 'processor_info' in result
        assert 'audio_analysis' in result
        
        # Check embedding
        assert isinstance(result['embedding'], list)
        assert len(result['embedding']) == 256
        
        # Check quality assessment
        quality = result['quality_assessment']
        assert 0.0 <= quality['overall_quality_score'] <= 1.0
        
        # Check processor info
        processor_info = result['processor_info']
        assert processor_info['processor_type'] in ['mock', 'resemblyzer']
        
        # Check audio analysis
        audio_analysis = result['audio_analysis']
        assert 'file_size_bytes' in audio_analysis
        assert 'format' in audio_analysis
    
    def test_process_audio_file_empty_data(self, sample_file_metadata):
        """Test processing empty audio data."""
        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            process_audio_file(b'', sample_file_metadata)
    
    def test_process_audio_file_invalid_metadata(self, sample_audio_data):
        """Test processing with invalid metadata."""
        with pytest.raises(ValueError, match="File metadata is required"):
            process_audio_file(sample_audio_data, {})
    
    def test_process_audio_file_with_mock_processor(self, sample_audio_data, sample_file_metadata):
        """Test processing with explicitly mocked processor."""
        with patch('utils.audio_processor.get_audio_processor') as mock_get_processor:
            mock_processor = Mock()
            mock_processor.generate_embedding.return_value = [0.1] * 256
            mock_processor.validate_audio_quality.return_value = {
                'is_valid': True,
                'overall_quality_score': 0.85,
                'snr_estimate': 25.5,
                'voice_activity_ratio': 0.92,
                'background_noise_level': 0.05,
                'quality_issues': []
            }
            mock_processor.get_processor_info.return_value = {
                'processor_type': 'mock',
                'processor_name': 'MockAudioProcessor',
                'processor_version': 'mock-1.0.0'
            }
            mock_get_processor.return_value = mock_processor
            
            result = process_audio_file(sample_audio_data, sample_file_metadata)
            
            assert result['embedding'] == [0.1] * 256
            assert result['quality_assessment']['overall_quality_score'] == 0.85


@pytest.mark.integration
class TestAudioProcessorIntegration:
    """Integration tests for audio processor components."""
    
    def test_full_audio_processing_pipeline(self, sample_audio_data, sample_file_metadata):
        """Test complete audio processing pipeline."""
        # Test with real MockAudioProcessor (no mocking)
        result = process_audio_file(sample_audio_data, sample_file_metadata)
        
        # Verify complete result structure
        assert 'embedding' in result
        assert 'quality_assessment' in result
        assert 'processor_info' in result
        assert 'audio_analysis' in result
        
        # Verify embedding characteristics
        embedding = result['embedding']
        assert len(embedding) == 256
        assert all(isinstance(x, float) for x in embedding)
        
        # Verify quality metrics are reasonable
        quality = result['quality_assessment']
        assert 0.0 <= quality['overall_quality_score'] <= 1.0
        assert quality['snr_estimate'] >= 0.0
        assert 0.0 <= quality['voice_activity_ratio'] <= 1.0
        
        # Verify processor info
        processor_info = result['processor_info']
        assert processor_info['processor_type'] == 'mock'
        assert 'processing_time_ms' in processor_info
    
    def test_audio_processor_consistency(self, sample_audio_data, sample_file_metadata):
        """Test that audio processor produces consistent results."""
        # Process same audio multiple times
        results = []
        for _ in range(3):
            result = process_audio_file(sample_audio_data, sample_file_metadata)
            results.append(result)
        
        # All embeddings should be identical (deterministic)
        embeddings = [r['embedding'] for r in results]
        assert all(emb == embeddings[0] for emb in embeddings)
        
        # Quality scores should be identical
        quality_scores = [r['quality_assessment']['overall_quality_score'] for r in results]
        assert all(score == quality_scores[0] for score in quality_scores)
    
    def test_different_audio_inputs_produce_different_embeddings(self, sample_file_metadata):
        """Test that different audio inputs produce different embeddings."""
        # Create different audio data
        audio_data_1 = b'RIFF' + b'\x00' * 1000 + b'audio1'
        audio_data_2 = b'RIFF' + b'\x00' * 1000 + b'audio2'
        
        result1 = process_audio_file(audio_data_1, sample_file_metadata)
        result2 = process_audio_file(audio_data_2, sample_file_metadata)
        
        # Embeddings should be different
        assert result1['embedding'] != result2['embedding']
