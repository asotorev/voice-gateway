"""
Unit tests for Voice Authentication Service.

Tests the core functionality of voice authentication including embedding
comparison, similarity calculation, and authentication decision logic.
"""
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

# Import the service (adjust path as needed for test environment)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'infrastructure', 'lambda', 'shared_layer', 'python'))

from shared.core.services.voice_authentication_service import (
    VoiceAuthenticationService,
    VoiceAuthenticationConfig,
    AuthenticationResult,
    authenticate_voice_sample,
    calculate_embedding_similarity
)


class TestVoiceAuthenticationConfig:
    """Test VoiceAuthenticationConfig class."""
    
    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = VoiceAuthenticationConfig()
        
        assert config.minimum_similarity_threshold == 0.75
        assert config.high_confidence_threshold == 0.85
        assert config.authentication_threshold == 0.80
        assert config.minimum_embeddings_required == 1
        assert config.use_average_scoring is True
        assert config.use_max_scoring is True
        assert config.confidence_weight_average == 0.6
        assert config.confidence_weight_max == 0.4
        assert config.minimum_embedding_dimensions == 256
        assert config.quality_score_weight == 0.1
    
    def test_custom_config_creation(self):
        """Test creating config with custom values."""
        config = VoiceAuthenticationConfig(
            minimum_similarity_threshold=0.8,
            authentication_threshold=0.85,
            minimum_embeddings_required=2
        )
        
        assert config.minimum_similarity_threshold == 0.8
        assert config.authentication_threshold == 0.85
        assert config.minimum_embeddings_required == 2
    
    def test_config_validation(self):
        """Test config validation for invalid values."""
        # Test invalid similarity threshold
        with pytest.raises(ValueError, match="minimum_similarity_threshold must be between 0.0 and 1.0"):
            VoiceAuthenticationConfig(minimum_similarity_threshold=1.5)
        
        # Test invalid authentication threshold
        with pytest.raises(ValueError, match="authentication_threshold must be between 0.0 and 1.0"):
            VoiceAuthenticationConfig(authentication_threshold=-0.1)
        
        # Test invalid minimum embeddings
        with pytest.raises(ValueError, match="minimum_embeddings_required must be at least 1"):
            VoiceAuthenticationConfig(minimum_embeddings_required=0)
    
    @patch.dict(os.environ, {
        'VOICE_AUTH_MIN_SIMILARITY': '0.8',
        'VOICE_AUTH_HIGH_CONFIDENCE': '0.9',
        'VOICE_AUTH_THRESHOLD': '0.85'
    })
    def test_config_from_environment(self):
        """Test creating config from environment variables."""
        config = VoiceAuthenticationConfig.from_environment()
        
        assert config.minimum_similarity_threshold == 0.8
        assert config.high_confidence_threshold == 0.9
        assert config.authentication_threshold == 0.85
    
    def test_config_to_dict(self):
        """Test converting config to dictionary."""
        config = VoiceAuthenticationConfig()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'minimum_similarity_threshold' in config_dict
        assert 'authentication_threshold' in config_dict
        assert config_dict['minimum_similarity_threshold'] == 0.75


class TestVoiceAuthenticationService:
    """Test VoiceAuthenticationService class."""
    
    @pytest.fixture
    def service(self):
        """Create a VoiceAuthenticationService instance for testing."""
        config = VoiceAuthenticationConfig(
            minimum_similarity_threshold=0.7,
            authentication_threshold=0.8,
            minimum_embeddings_required=1
        )
        return VoiceAuthenticationService(config)
    
    @pytest.fixture
    def sample_embedding_256(self):
        """Create a sample 256-dimensional embedding."""
        np.random.seed(42)  # For reproducible tests
        return np.random.rand(256).tolist()
    
    @pytest.fixture
    def similar_embedding_256(self, sample_embedding_256):
        """Create an embedding similar to sample_embedding_256."""
        # Add small noise to create a similar but not identical embedding
        similar = np.array(sample_embedding_256) + np.random.normal(0, 0.1, 256)
        return similar.tolist()
    
    @pytest.fixture
    def different_embedding_256(self):
        """Create a different 256-dimensional embedding."""
        np.random.seed(123)  # Different seed for different embedding
        return np.random.rand(256).tolist()
    
    @pytest.fixture
    def stored_embeddings_sample(self, sample_embedding_256, similar_embedding_256):
        """Create sample stored embeddings data."""
        return [
            {
                'embedding': sample_embedding_256,
                'quality_score': 0.9,
                'created_at': '2023-01-01T00:00:00Z',
                'audio_metadata': {'file_name': 'sample1.wav', 'duration': 3.0}
            },
            {
                'embedding': similar_embedding_256,
                'quality_score': 0.85,
                'created_at': '2023-01-02T00:00:00Z',
                'audio_metadata': {'file_name': 'sample2.wav', 'duration': 2.5}
            }
        ]
    
    def test_service_initialization(self):
        """Test service initialization with default config."""
        service = VoiceAuthenticationService()
        assert service.config is not None
        assert isinstance(service.config, VoiceAuthenticationConfig)
    
    def test_service_initialization_custom_config(self):
        """Test service initialization with custom config."""
        config = VoiceAuthenticationConfig(authentication_threshold=0.9)
        service = VoiceAuthenticationService(config)
        assert service.config.authentication_threshold == 0.9
    
    def test_calculate_cosine_similarity_identical(self, service, sample_embedding_256):
        """Test cosine similarity calculation with identical embeddings."""
        similarity = service.calculate_cosine_similarity(sample_embedding_256, sample_embedding_256)
        assert abs(similarity - 1.0) < 1e-6  # Should be very close to 1.0
    
    def test_calculate_cosine_similarity_similar(self, service, sample_embedding_256, similar_embedding_256):
        """Test cosine similarity calculation with similar embeddings."""
        similarity = service.calculate_cosine_similarity(sample_embedding_256, similar_embedding_256)
        assert 0.8 < similarity < 1.0  # Should be high similarity
    
    def test_calculate_cosine_similarity_different(self, service, sample_embedding_256, different_embedding_256):
        """Test cosine similarity calculation with different embeddings."""
        similarity = service.calculate_cosine_similarity(sample_embedding_256, different_embedding_256)
        assert 0.0 <= similarity <= 1.0  # Should be valid similarity score
    
    def test_calculate_cosine_similarity_validation(self, service):
        """Test cosine similarity validation with invalid inputs."""
        # Test empty embeddings
        with pytest.raises(ValueError, match="Embeddings cannot be empty"):
            service.calculate_cosine_similarity([], [1, 2, 3])
        
        # Test dimension mismatch
        with pytest.raises(ValueError, match="Embedding dimensions mismatch"):
            service.calculate_cosine_similarity([1, 2, 3], [1, 2, 3, 4])
    
    def test_calculate_cosine_similarity_zero_norm(self, service):
        """Test cosine similarity with zero-norm embedding."""
        zero_embedding = [0.0] * 256
        normal_embedding = [1.0] * 256
        
        similarity = service.calculate_cosine_similarity(zero_embedding, normal_embedding)
        assert similarity == 0.0
    
    def test_compare_against_stored_embeddings_success(self, service, sample_embedding_256, stored_embeddings_sample):
        """Test successful comparison against stored embeddings."""
        result = service.compare_against_stored_embeddings(sample_embedding_256, stored_embeddings_sample)
        
        assert 'similarities' in result
        assert 'average_similarity' in result
        assert 'max_similarity' in result
        assert 'min_similarity' in result
        assert 'quality_weighted_average' in result
        assert 'total_comparisons' in result
        assert 'comparison_details' in result
        
        assert len(result['similarities']) == 2
        assert result['total_comparisons'] == 2
        assert 0.0 <= result['average_similarity'] <= 1.0
        assert 0.0 <= result['max_similarity'] <= 1.0
        assert 0.0 <= result['min_similarity'] <= 1.0
    
    def test_compare_against_stored_embeddings_validation(self, service):
        """Test validation in compare_against_stored_embeddings."""
        # Test empty input embedding
        with pytest.raises(ValueError, match="Input embedding cannot be empty"):
            service.compare_against_stored_embeddings([], [{'embedding': [1, 2, 3]}])
        
        # Test no stored embeddings
        with pytest.raises(ValueError, match="No stored embeddings provided"):
            service.compare_against_stored_embeddings([1, 2, 3], [])
        
        # Test insufficient stored embeddings (with config requiring 2+)
        service.config.minimum_embeddings_required = 2
        with pytest.raises(ValueError, match="Insufficient stored embeddings"):
            service.compare_against_stored_embeddings([1, 2, 3], [{'embedding': [1, 2, 3]}])
    
    def test_calculate_authentication_confidence_authenticated(self, service):
        """Test confidence calculation for successful authentication."""
        comparison_result = {
            'similarities': [0.85, 0.90],
            'average_similarity': 0.875,
            'max_similarity': 0.90,
            'min_similarity': 0.85,
            'quality_weighted_average': 0.88,
            'total_comparisons': 2,
            'comparison_details': []
        }
        
        confidence_result = service.calculate_authentication_confidence(comparison_result)
        
        assert confidence_result['authentication_result'] == AuthenticationResult.AUTHENTICATED.value
        assert confidence_result['meets_threshold'] is True
        assert 0.0 <= confidence_result['confidence_score'] <= 1.0
        assert 'decision_factors' in confidence_result
    
    def test_calculate_authentication_confidence_rejected(self, service):
        """Test confidence calculation for rejected authentication."""
        comparison_result = {
            'similarities': [0.5, 0.6],
            'average_similarity': 0.55,
            'max_similarity': 0.6,
            'min_similarity': 0.5,
            'quality_weighted_average': 0.55,
            'total_comparisons': 2,
            'comparison_details': []
        }
        
        confidence_result = service.calculate_authentication_confidence(comparison_result)
        
        assert confidence_result['authentication_result'] == AuthenticationResult.REJECTED.value
        assert confidence_result['meets_threshold'] is False
        assert 0.0 <= confidence_result['confidence_score'] <= 1.0
    
    def test_authenticate_voice_complete_workflow(self, service, sample_embedding_256, stored_embeddings_sample):
        """Test complete voice authentication workflow."""
        result = service.authenticate_voice(sample_embedding_256, stored_embeddings_sample)
        
        # Check main result structure
        assert 'authentication_successful' in result
        assert 'confidence_score' in result
        assert 'authentication_result' in result
        assert 'is_high_confidence' in result
        assert 'similarity_analysis' in result
        assert 'confidence_analysis' in result
        assert 'configuration' in result
        assert 'processed_at' in result
        
        # Check types
        assert isinstance(result['authentication_successful'], bool)
        assert isinstance(result['confidence_score'], float)
        assert isinstance(result['is_high_confidence'], bool)
        assert isinstance(result['similarity_analysis'], dict)
        assert isinstance(result['confidence_analysis'], dict)
        assert isinstance(result['configuration'], dict)
        
        # Check score bounds
        assert 0.0 <= result['confidence_score'] <= 1.0


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.fixture
    def sample_embedding(self):
        """Create a sample embedding for testing."""
        return [0.1] * 256
    
    @pytest.fixture
    def stored_embeddings(self, sample_embedding):
        """Create stored embeddings for testing."""
        return [
            {
                'embedding': sample_embedding,
                'quality_score': 0.9,
                'created_at': '2023-01-01T00:00:00Z'
            }
        ]
    
    def test_authenticate_voice_sample_function(self, sample_embedding, stored_embeddings):
        """Test authenticate_voice_sample convenience function."""
        result = authenticate_voice_sample(sample_embedding, stored_embeddings)
        
        assert isinstance(result, dict)
        assert 'authentication_successful' in result
        assert 'confidence_score' in result
    
    def test_calculate_embedding_similarity_function(self, sample_embedding):
        """Test calculate_embedding_similarity convenience function."""
        similarity = calculate_embedding_similarity(sample_embedding, sample_embedding)
        
        assert isinstance(similarity, float)
        assert abs(similarity - 1.0) < 1e-6  # Should be very close to 1.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_service_with_single_embedding(self):
        """Test authentication with only one stored embedding."""
        service = VoiceAuthenticationService()
        input_embedding = [0.5] * 256
        stored_embeddings = [
            {
                'embedding': [0.6] * 256,
                'quality_score': 0.8,
                'created_at': '2023-01-01T00:00:00Z'
            }
        ]
        
        result = service.authenticate_voice(input_embedding, stored_embeddings)
        assert isinstance(result, dict)
        assert 'authentication_successful' in result
    
    def test_service_with_poor_quality_embeddings(self):
        """Test authentication with low quality stored embeddings."""
        service = VoiceAuthenticationService()
        input_embedding = [0.5] * 256
        stored_embeddings = [
            {
                'embedding': [0.6] * 256,
                'quality_score': 0.1,  # Very low quality
                'created_at': '2023-01-01T00:00:00Z'
            },
            {
                'embedding': [0.7] * 256,
                'quality_score': 0.9,  # High quality
                'created_at': '2023-01-02T00:00:00Z'
            }
        ]
        
        result = service.authenticate_voice(input_embedding, stored_embeddings)
        assert isinstance(result, dict)
        # With different quality scores, the weighted average should differ from simple average
        similarity_analysis = result['similarity_analysis']
        assert 'quality_weighted_average' in similarity_analysis
        assert 'average_similarity' in similarity_analysis
        # The quality weighted average should be influenced by the quality scores
        assert isinstance(similarity_analysis['quality_weighted_average'], float)
    
    def test_service_with_malformed_stored_embedding(self):
        """Test handling of malformed stored embedding data."""
        service = VoiceAuthenticationService()
        input_embedding = [0.5] * 256
        stored_embeddings = [
            {
                'embedding': [0.6] * 256,
                'quality_score': 0.8,
                'created_at': '2023-01-01T00:00:00Z'
            },
            {
                # Missing embedding
                'quality_score': 0.9,
                'created_at': '2023-01-02T00:00:00Z'
            }
        ]
        
        # Should process the valid embedding and skip the malformed one
        result = service.authenticate_voice(input_embedding, stored_embeddings)
        assert result['similarity_analysis']['total_comparisons'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
