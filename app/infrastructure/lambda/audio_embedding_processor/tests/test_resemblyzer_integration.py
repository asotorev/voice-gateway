"""
Unit and integration tests for Resemblyzer audio processor.

Tests the ResemblyzerAudioProcessor implementation including embedding generation,
quality validation, and audio preprocessing functionality.
"""
import pytest
import numpy as np
from unittest.mock import patch, Mock
from .conftest import create_resemblyzer_mocks
from utils.audio_processor import (
    ResemblyzerAudioProcessor, 
    get_audio_processor,
    RESEMBLYZER_AVAILABLE
)


@pytest.mark.skipif(not RESEMBLYZER_AVAILABLE, reason="Resemblyzer dependencies not available")
@pytest.mark.unit
class TestResemblyzerAudioProcessor:
    """Test cases for ResemblyzerAudioProcessor."""
    
    def setup_method(self):
        """Setup test instance."""
        # Get centralized Resemblyzer mocks
        resemblyzer_mocks = create_resemblyzer_mocks()
        
        with patch('utils.audio_processor.VoiceEncoder', resemblyzer_mocks['VoiceEncoder']):
            resemblyzer_mocks['VoiceEncoder'].return_value = Mock()
            self.processor = ResemblyzerAudioProcessor()
    
    def test_initialization_success(self):
        """Test successful ResemblyzerAudioProcessor initialization."""
        # Get centralized Resemblyzer mocks
        resemblyzer_mocks = create_resemblyzer_mocks()
        
        with patch('utils.audio_processor.VoiceEncoder', resemblyzer_mocks['VoiceEncoder']):
            resemblyzer_mocks['VoiceEncoder'].return_value = Mock()
            
            processor = ResemblyzerAudioProcessor()
            
            assert processor.embedding_dimensions == 256
            assert processor.processor_version == "resemblyzer-1.0.0"
            assert processor.target_sample_rate == 16000
            assert processor.min_audio_length == 1.0
            assert processor.max_audio_length == 30.0
            resemblyzer_mocks['VoiceEncoder'].assert_called_once()
    
    def test_initialization_failure(self):
        """Test ResemblyzerAudioProcessor initialization failure."""
        # Get centralized Resemblyzer mocks
        resemblyzer_mocks = create_resemblyzer_mocks()
        
        with patch('utils.audio_processor.VoiceEncoder', resemblyzer_mocks['VoiceEncoder']):
            resemblyzer_mocks['VoiceEncoder'].side_effect = RuntimeError("Model loading failed")
            
            with pytest.raises(RuntimeError, match="Resemblyzer initialization failed"):
                ResemblyzerAudioProcessor()
    
    def test_generate_embedding_success(self, sample_audio_data, sample_file_metadata):
        """Test successful embedding generation."""
        # Mock the encoder and preprocessing
        mock_embedding = np.random.rand(256)
        self.processor.encoder.embed_utterance = Mock(return_value=mock_embedding)
        self.processor._preprocess_audio = Mock(return_value=np.random.rand(16000))
        
        embedding = self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 256
        assert all(isinstance(x, float) for x in embedding)
        self.processor._preprocess_audio.assert_called_once()
        self.processor.encoder.embed_utterance.assert_called_once()
    
    def test_generate_embedding_preprocessing_failure(self, sample_audio_data, sample_file_metadata):
        """Test embedding generation with preprocessing failure."""
        self.processor._preprocess_audio = Mock(side_effect=ValueError("Invalid audio"))
        
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
    
    def test_generate_embedding_encoder_failure(self, sample_audio_data, sample_file_metadata):
        """Test embedding generation with encoder failure."""
        self.processor._preprocess_audio = Mock(return_value=np.random.rand(16000))
        self.processor.encoder.embed_utterance = Mock(side_effect=RuntimeError("Encoder failed"))
        
        with pytest.raises(RuntimeError, match="Embedding generation failed"):
            self.processor.generate_embedding(sample_audio_data, sample_file_metadata)
    
    def test_validate_audio_quality_success(self, sample_audio_data, sample_file_metadata):
        """Test successful audio quality validation."""
        # Mock audio loading and analysis
        mock_wav_data = np.random.rand(16000)  # 1 second at 16kHz
        mock_sample_rate = 16000
        
        self.processor._load_audio_for_analysis = Mock(return_value=(mock_wav_data, mock_sample_rate))
        self.processor._analyze_signal_quality = Mock(return_value={
            'snr_estimate': 25.0,
            'dynamic_range': 0.8,
            'zero_crossing_rate': 0.1,
            'rms_level': 0.15
        })
        self.processor._detect_voice_activity = Mock(return_value=0.8)
        
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        assert result['is_valid'] is True
        assert 'overall_quality_score' in result
        assert 0.0 <= result['overall_quality_score'] <= 1.0
        assert result['metrics']['duration_seconds'] == 1.0
        assert result['metrics']['sample_rate'] == 16000
        assert result['metrics']['voice_activity_ratio'] == 0.8
    
    def test_validate_audio_quality_too_short(self, sample_audio_data, sample_file_metadata):
        """Test audio quality validation with audio too short."""
        # Mock short audio (0.5 seconds)
        mock_wav_data = np.random.rand(8000)  # 0.5 seconds at 16kHz
        mock_sample_rate = 16000
        
        self.processor._load_audio_for_analysis = Mock(return_value=(mock_wav_data, mock_sample_rate))
        
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any("too short" in issue for issue in result['issues'])
    
    def test_validate_audio_quality_low_sample_rate(self, sample_audio_data, sample_file_metadata):
        """Test audio quality validation with low sample rate."""
        # Mock low sample rate audio
        mock_wav_data = np.random.rand(8000)  # 1 second at 8kHz
        mock_sample_rate = 4000  # Very low sample rate
        
        self.processor._load_audio_for_analysis = Mock(return_value=(mock_wav_data, mock_sample_rate))
        
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any("Sample rate too low" in issue for issue in result['issues'])
    
    def test_validate_audio_quality_validation_failure(self, sample_audio_data, sample_file_metadata):
        """Test audio quality validation with analysis failure."""
        self.processor._load_audio_for_analysis = Mock(side_effect=ValueError("Load failed"))
        
        result = self.processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
        
        # Should return permissive result on failure
        assert result['is_valid'] is True
        assert result['overall_quality_score'] == 0.7
        assert any("Quality validation failed" in warning for warning in result['warnings'])
    
    def test_get_processor_info(self):
        """Test processor info retrieval."""
        info = self.processor.get_processor_info()
        
        assert info['processor_type'] == 'resemblyzer'
        assert info['processor_name'] == 'ResemblyzerAudioProcessor'
        assert info['embedding_dimensions'] == 256
        assert info['status'] == 'active'
        assert 'voice_embeddings' in info['capabilities']
        assert info['model_info']['framework'] == 'pytorch'
        assert info['quality_requirements']['target_sample_rate'] == 16000


@pytest.mark.skipif(not RESEMBLYZER_AVAILABLE, reason="Resemblyzer dependencies not available")
@pytest.mark.unit
class TestResemblyzerAudioPreprocessing:
    """Test cases for Resemblyzer audio preprocessing methods."""
    
    def setup_method(self):
        """Setup test instance."""
        with patch('utils.audio_processor.VoiceEncoder') as mock_encoder:
            mock_encoder.return_value = Mock()
            self.processor = ResemblyzerAudioProcessor()
    
    def test_preprocess_audio_success(self, sample_file_metadata):
        """Test successful audio preprocessing."""
        mock_wav_data = np.random.rand(16000).astype(np.float32)
        mock_sample_rate = 16000
        mock_preprocessed = np.random.rand(16000)
        
        self.processor._load_audio_for_analysis = Mock(return_value=(mock_wav_data, mock_sample_rate))
        
        with patch('utils.audio_processor.preprocess_wav', return_value=mock_preprocessed) as mock_preprocess:
            result = self.processor._preprocess_audio(b'fake_audio_data', sample_file_metadata)
            
            assert isinstance(result, np.ndarray)
            mock_preprocess.assert_called_once()
            self.processor._load_audio_for_analysis.assert_called_once()
    
    def test_preprocess_audio_resample(self, sample_file_metadata):
        """Test audio preprocessing with resampling."""
        mock_wav_data = np.random.rand(44100).astype(np.float32)  # 44.1kHz
        mock_sample_rate = 44100
        mock_resampled = np.random.rand(16000).astype(np.float32)
        mock_preprocessed = np.random.rand(16000)
        
        self.processor._load_audio_for_analysis = Mock(return_value=(mock_wav_data, mock_sample_rate))
        
        with patch('utils.audio_processor.librosa.resample', return_value=mock_resampled) as mock_resample, \
             patch('utils.audio_processor.preprocess_wav', return_value=mock_preprocessed) as mock_preprocess:
            
            result = self.processor._preprocess_audio(b'fake_audio_data', sample_file_metadata)
            
            mock_resample.assert_called_once_with(mock_wav_data, orig_sr=44100, target_sr=16000)
            mock_preprocess.assert_called_once()
    
    def test_preprocess_audio_truncate_long(self, sample_file_metadata):
        """Test audio preprocessing with long audio truncation."""
        # Create 35 seconds of audio (longer than max_audio_length=30)
        long_audio = np.random.rand(35 * 16000).astype(np.float32)
        mock_sample_rate = 16000
        
        self.processor._load_audio_for_analysis = Mock(return_value=(long_audio, mock_sample_rate))
        
        with patch('utils.audio_processor.preprocess_wav') as mock_preprocess:
            self.processor._preprocess_audio(b'fake_audio_data', sample_file_metadata)
            
            # Check that audio was truncated
            processed_audio_arg = mock_preprocess.call_args[0][0]
            expected_length = int(30 * 16000)  # 30 seconds
            assert len(processed_audio_arg) <= expected_length
    
    def test_load_audio_for_analysis_success(self):
        """Test successful audio loading."""
        fake_audio_data = b'RIFF' + b'\x00' * 1000  # Fake WAV data
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('utils.audio_processor.sf.read') as mock_sf_read, \
             patch('os.unlink') as mock_unlink:
            
            # Setup mocks
            mock_file = Mock()
            mock_file.name = '/tmp/test.wav'
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_sf_read.return_value = (np.random.rand(16000), 16000)
            
            wav_data, sample_rate = self.processor._load_audio_for_analysis(fake_audio_data)
            
            assert isinstance(wav_data, np.ndarray)
            assert wav_data.dtype == np.float32
            assert sample_rate == 16000
            mock_file.write.assert_called_once_with(fake_audio_data)
            mock_unlink.assert_called_once_with('/tmp/test.wav')
    
    def test_load_audio_for_analysis_fallback(self):
        """Test audio loading with fallback to librosa."""
        fake_audio_data = b'fake_audio'
        
        with patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('utils.audio_processor.sf.read', side_effect=Exception("SF failed")), \
             patch('utils.audio_processor.librosa.load') as mock_librosa:
            
            mock_file = Mock()
            mock_temp.return_value.__enter__.return_value = mock_file
            mock_librosa.return_value = (np.random.rand(16000), 16000)
            
            wav_data, sample_rate = self.processor._load_audio_for_analysis(fake_audio_data)
            
            assert isinstance(wav_data, np.ndarray)
            mock_librosa.assert_called_once()


@pytest.mark.unit
class TestGetAudioProcessorWithResemblyzer:
    """Test audio processor factory with Resemblyzer."""
    
    def test_get_resemblyzer_processor(self):
        """Test getting Resemblyzer processor."""
        with patch.dict('os.environ', {'EMBEDDING_PROCESSOR_TYPE': 'resemblyzer'}), \
             patch('utils.audio_processor.RESEMBLYZER_AVAILABLE', True), \
             patch('utils.audio_processor.VoiceEncoder'):
            
            processor = get_audio_processor()
            
            assert isinstance(processor, ResemblyzerAudioProcessor)
    
    def test_get_resemblyzer_processor_unavailable(self):
        """Test getting processor when Resemblyzer unavailable."""
        with patch.dict('os.environ', {'EMBEDDING_PROCESSOR_TYPE': 'resemblyzer'}), \
             patch('utils.audio_processor.RESEMBLYZER_AVAILABLE', False):
            
            # Should fall back to mock processor
            with pytest.raises(ImportError, match="Resemblyzer dependencies not available"):
                get_audio_processor()


@pytest.mark.skipif(not RESEMBLYZER_AVAILABLE, reason="Resemblyzer dependencies not available")
@pytest.mark.integration
class TestResemblyzerIntegration:
    """Integration tests for Resemblyzer processor."""
    
    def test_full_resemblyzer_pipeline(self, sample_audio_data, sample_file_metadata):
        """Test complete Resemblyzer processing pipeline."""
        with patch('utils.audio_processor.VoiceEncoder') as mock_encoder_class:
            # Setup mock encoder
            mock_encoder = Mock()
            mock_embedding = np.random.rand(256)
            mock_encoder.embed_utterance.return_value = mock_embedding
            mock_encoder_class.return_value = mock_encoder
            
            # Mock audio loading
            mock_wav_data = np.random.rand(16000).astype(np.float32)
            
            with patch.object(ResemblyzerAudioProcessor, '_load_audio_for_analysis', 
                            return_value=(mock_wav_data, 16000)), \
                 patch('utils.audio_processor.preprocess_wav', return_value=mock_wav_data):
                
                processor = ResemblyzerAudioProcessor()
                
                # Test embedding generation
                embedding = processor.generate_embedding(sample_audio_data, sample_file_metadata)
                assert len(embedding) == 256
                assert all(isinstance(x, float) for x in embedding)
                
                # Test quality validation
                quality_result = processor.validate_audio_quality(sample_audio_data, sample_file_metadata)
                assert 'overall_quality_score' in quality_result
                
                # Test processor info
                info = processor.get_processor_info()
                assert info['processor_type'] == 'resemblyzer'
                assert info['status'] == 'active'
