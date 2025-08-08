"""
Unit tests for AudioFileValidator.

Tests file validation including format, size, security checks,
and content validation.
"""
import pytest
from unittest.mock import patch
from utils.file_validator import AudioFileValidator


@pytest.mark.unit
class TestAudioFileValidator:
    """Test cases for AudioFileValidator."""
    
    def setup_method(self):
        """Setup test instance."""
        self.validator = AudioFileValidator()
    
    def test_initialization(self):
        """Test validator initialization with default settings."""
        validator = AudioFileValidator()
        
        assert validator.max_file_size > 0
        assert validator.min_file_size > 0
        assert len(validator.supported_formats) > 0
        assert 'wav' in validator.supported_formats
    
    def test_validate_file_success(self, sample_audio_data, sample_file_metadata):
        """Test successful file validation."""
        result = self.validator.validate_file(sample_audio_data, sample_file_metadata)
        
        assert result['is_valid'] is True
        assert len(result['validation_passed']) > 0
        assert len(result['validation_failed']) == 0
        assert 'validated_at' in result
    
    def test_validate_file_empty_file(self, sample_file_metadata):
        """Test validation of empty file."""
        empty_data = b''
        
        result = self.validator.validate_file(empty_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any('empty' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_file_too_large(self, sample_file_metadata):
        """Test validation of file that's too large."""
        # Create file larger than max size (default 10MB)
        large_data = b'x' * (11 * 1024 * 1024)
        
        result = self.validator.validate_file(large_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any('too large' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_file_too_small(self, sample_file_metadata):
        """Test validation of file that's too small."""
        small_data = b'x' * 500  # Less than 1KB minimum
        
        result = self.validator.validate_file(small_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any('too small' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_file_unsupported_format(self, sample_audio_data):
        """Test validation of unsupported file format."""
        metadata = {
            'file_name': 'test.txt',  # Unsupported format
            'size_bytes': len(sample_audio_data),
            'content_type': 'text/plain'
        }
        
        result = self.validator.validate_file(sample_audio_data, metadata)
        
        assert result['is_valid'] is False
        assert any('unsupported format' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_file_no_extension(self, sample_audio_data):
        """Test validation of file with no extension."""
        metadata = {
            'file_name': 'test_file_no_extension',
            'size_bytes': len(sample_audio_data),
            'content_type': 'audio/wav'
        }
        
        result = self.validator.validate_file(sample_audio_data, metadata)
        
        assert result['is_valid'] is False
        assert any('no file extension' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_wav_header_success(self, sample_file_metadata):
        """Test validation of valid WAV file header."""
        # Create valid WAV header
        wav_data = b'RIFF' + (1000).to_bytes(4, 'little') + b'WAVE'
        wav_data += b'fmt ' + (16).to_bytes(4, 'little')
        wav_data += b'data' + (500).to_bytes(4, 'little')
        wav_data += b'\x00' * 500
        
        result = self.validator.validate_file(wav_data, sample_file_metadata)
        
        assert result['is_valid'] is True
        assert any('header validation' in passed.lower() for passed in result['validation_passed'])
    
    def test_validate_wav_header_mismatch(self, sample_file_metadata):
        """Test validation of file with mismatched header."""
        # Create MP3-like header but with .wav extension
        mp3_data = b'ID3' + b'\x03\x00\x00\x00' + b'\x00' * 1000
        
        result = self.validator.validate_file(mp3_data, sample_file_metadata)
        
        # Should still be valid but with warnings
        assert result['is_valid'] is True
        assert len(result['warnings']) > 0
    
    def test_security_check_executable_signature(self, sample_file_metadata):
        """Test security check for executable signatures."""
        # Create data with Windows PE signature
        malicious_data = b'MZ' + b'\x00' * 1000
        
        result = self.validator.validate_file(malicious_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any('executable signature' in failure.lower() for failure in result['validation_failed'])
    
    def test_security_check_script_patterns(self, sample_file_metadata):
        """Test security check for script patterns."""
        # Create data with script tag
        script_data = b'<script>alert("test")</script>' + b'\x00' * 1000
        
        result = self.validator.validate_file(script_data, sample_file_metadata)
        
        assert result['is_valid'] is False
        assert any('script pattern' in failure.lower() for failure in result['validation_failed'])
    
    def test_validate_file_exception_handling(self, sample_file_metadata):
        """Test validator exception handling."""
        with patch.object(self.validator, '_validate_file_size') as mock_validate:
            mock_validate.side_effect = Exception("Test exception")
            
            result = self.validator.validate_file(b'test', sample_file_metadata)
            
            assert result['is_valid'] is False
            assert any('validation exception' in failure.lower() for failure in result['validation_failed'])
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        # Test normal cases
        assert self.validator._get_file_extension('test.wav') == 'wav'
        assert self.validator._get_file_extension('file.mp3') == 'mp3'
        assert self.validator._get_file_extension('path/to/file.flac') == 'flac'
        
        # Test edge cases
        assert self.validator._get_file_extension('no_extension') == ''
        assert self.validator._get_file_extension('multiple.dots.wav') == 'wav'
        assert self.validator._get_file_extension('') == ''
    
    def test_validation_with_different_audio_formats(self):
        """Test validation with different supported audio formats."""
        formats_and_headers = [
            ('wav', b'RIFF' + b'\x00' * 4 + b'WAVE'),
            ('mp3', b'ID3' + b'\x00' * 5),
            ('flac', b'fLaC' + b'\x00' * 4),
            ('m4a', b'ftypM4A ' + b'\x00' * 4)
        ]
        
        for format_name, header in formats_and_headers:
            metadata = {
                'file_name': f'test.{format_name}',
                'size_bytes': 5000,
                'content_type': f'audio/{format_name}'
            }
            
            # Create test data with proper header
            test_data = header + b'\x00' * 4900
            
            result = self.validator.validate_file(test_data, metadata)
            
            # Should pass format validation
            assert result['is_valid'] is True, f"Failed for format: {format_name}"
    
    def test_file_size_validation_edge_cases(self):
        """Test file size validation with edge cases."""
        metadata = {'file_name': 'test.wav', 'content_type': 'audio/wav'}
        
        # Test exactly at minimum size
        min_size_data = b'\x00' * self.validator.min_file_size
        result = self.validator.validate_file(min_size_data, metadata)
        assert result['is_valid'] is True
        
        # Test one byte under minimum
        under_min_data = b'\x00' * (self.validator.min_file_size - 1)
        result = self.validator.validate_file(under_min_data, metadata)
        assert result['is_valid'] is False
    
    def test_concurrent_validation(self, sample_audio_data, sample_file_metadata):
        """Test that validator handles concurrent validation calls."""
        import threading
        
        results = []
        errors = []
        
        def validate_file():
            try:
                result = self.validator.validate_file(sample_audio_data, sample_file_metadata)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Run multiple validations concurrently
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_file)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # All validations should succeed
        assert len(errors) == 0
        assert len(results) == 5
        assert all(result['is_valid'] for result in results)


@pytest.mark.integration
class TestFileValidatorIntegration:
    """Integration tests for file validator."""
    
    def test_validate_real_audio_formats(self):
        """Test validation with real audio format examples."""
        # This would test with real audio file samples
        # For now, we'll test with our mock data
        validator = AudioFileValidator()
        
        # Test with sample that should pass all validations
        wav_header = b'RIFF' + (5000).to_bytes(4, 'little') + b'WAVE'
        wav_header += b'fmt ' + (16).to_bytes(4, 'little')
        wav_data = wav_header + b'\x00' * 4980
        
        metadata = {
            'file_name': 'integration_test.wav',
            'size_bytes': len(wav_data),
            'content_type': 'audio/wav'
        }
        
        result = validator.validate_file(wav_data, metadata)
        
        assert result['is_valid'] is True
        assert len(result['validation_passed']) >= 3  # Size, format, header, security
        assert len(result['validation_failed']) == 0
    
    def test_validate_with_custom_settings(self):
        """Test validation with custom environment settings."""
        with patch('os.getenv') as mock_getenv:
            # Mock custom settings
            mock_getenv.side_effect = lambda key, default: {
                'MAX_AUDIO_FILE_SIZE_MB': '5',  # Smaller max size
                'SUPPORTED_AUDIO_FORMATS': 'wav,mp3',  # Fewer formats
                'MIN_AUDIO_DURATION_SECONDS': '2',
                'MAX_AUDIO_DURATION_SECONDS': '60'
            }.get(key, default)
            
            validator = AudioFileValidator()
            
            # Test with file that would exceed new limit
            large_data = b'RIFF' + b'\x00' * 4 + b'WAVE' + b'\x00' * (6 * 1024 * 1024)
            metadata = {
                'file_name': 'large.wav',
                'size_bytes': len(large_data),
                'content_type': 'audio/wav'
            }
            
            result = validator.validate_file(large_data, metadata)
            
            assert result['is_valid'] is False
            assert any('too large' in failure.lower() for failure in result['validation_failed'])
