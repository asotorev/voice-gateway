#!/usr/bin/env python3
"""
Local test script for Resemblyzer integration.

This script allows testing the Resemblyzer audio processor locally
before deploying to Lambda. Useful for development and debugging.

Usage:
    python test_resemblyzer_local.py
    
    # Or test with specific processor type:
    EMBEDDING_PROCESSOR_TYPE=resemblyzer python test_resemblyzer_local.py
    EMBEDDING_PROCESSOR_TYPE=mock python test_resemblyzer_local.py
"""
import os
import sys
import logging
import tempfile
import wave
import struct
import traceback
from pathlib import Path

# Try to import optional dependencies
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import resemblyzer
    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_fake_audio_data() -> bytes:
    """Create fake WAV audio data for testing."""
    try:
        # WAV file parameters
        sample_rate = 16000
        duration = 3.0  # 3 seconds
        frequency = 440  # A4 note
        
        # Generate sine wave
        samples = int(sample_rate * duration)
        audio_data = []
        
        for i in range(samples):
            # Generate sine wave with some noise
            sine_wave = np.sin(2 * np.pi * frequency * i / sample_rate)
            noise = np.random.normal(0, 0.1)  # Add some noise
            sample = int((sine_wave + noise) * 32767 / 2)  # Convert to 16-bit
            audio_data.append(struct.pack('<h', sample))
        
        # Create WAV file in memory
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            with wave.open(temp_file.name, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(b''.join(audio_data))
            
            # Read back as bytes
            temp_file.seek(0)
            with open(temp_file.name, 'rb') as f:
                audio_bytes = f.read()
            
            # Cleanup
            os.unlink(temp_file.name)
            
            return audio_bytes
            
    except Exception as e:
        logger.warning(f"Failed to create synthetic audio: {e}")
        # Return simple fake WAV header + data
        return b'RIFF\x00\x10\x00\x00WAVEfmt \x00\x00\x00\x00data\x00\x00\x00\x00' + b'\x00' * 48000


def test_audio_processor():
    """Test audio processor functionality."""
    try:
        from utils.audio_processor import get_audio_processor, RESEMBLYZER_AVAILABLE
        
        logger.info("Testing audio processor integration...")
        
        # Check processor type
        processor_type = os.getenv('EMBEDDING_PROCESSOR_TYPE', 'mock')
        logger.info(f"Processor type: {processor_type}")
        logger.info(f"Resemblyzer available: {RESEMBLYZER_AVAILABLE}")
        
        # Create fake audio data
        logger.info("Creating test audio data...")
        audio_data = create_fake_audio_data()
        
        file_metadata = {
            'file_name': 'test_sample.wav',
            'size_bytes': len(audio_data),
            'content_type': 'audio/wav'
        }
        
        logger.info(f"Test audio size: {len(audio_data)} bytes")
        
        # Get processor
        logger.info("Initializing audio processor...")
        processor = get_audio_processor()
        
        # Test processor info
        info = processor.get_processor_info()
        logger.info(f"Processor info: {info['processor_type']} v{info['processor_version']}")
        logger.info(f"Embedding dimensions: {info['embedding_dimensions']}")
        logger.info(f"Capabilities: {info.get('capabilities', [])}")
        
        # Test quality validation
        logger.info("Testing audio quality validation...")
        quality_result = processor.validate_audio_quality(audio_data, file_metadata)
        logger.info(f"Quality validation - Valid: {quality_result['is_valid']}")
        logger.info(f"Quality score: {quality_result['overall_quality_score']:.3f}")
        
        if quality_result['issues']:
            logger.warning(f"Quality issues: {quality_result['issues']}")
        if quality_result['warnings']:
            logger.info(f"Quality warnings: {quality_result['warnings']}")
        
        # Test embedding generation
        logger.info("Testing embedding generation...")
        embedding = processor.generate_embedding(audio_data, file_metadata)
        
        logger.info(f"Embedding generated successfully!")
        logger.info(f"Embedding dimensions: {len(embedding)}")
        logger.info(f"Embedding type: {type(embedding[0]) if embedding else 'empty'}")
        logger.info(f"Embedding range: [{min(embedding):.3f}, {max(embedding):.3f}]")
        logger.info(f"Embedding norm: {np.linalg.norm(embedding):.3f}")
        
        # Test second embedding for consistency
        logger.info("Testing embedding consistency...")
        embedding2 = processor.generate_embedding(audio_data, file_metadata)
        
        if processor_type == 'mock':
            # Mock processor should be deterministic
            is_identical = embedding == embedding2
            logger.info(f"Embeddings identical (deterministic): {is_identical}")
        else:
            # Real processor might have small variations
            similarity = np.dot(embedding, embedding2) / (np.linalg.norm(embedding) * np.linalg.norm(embedding2))
            logger.info(f"Embedding cosine similarity: {similarity:.3f}")
        
        logger.info("Audio processor test completed successfully!")
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.info("This is expected if Resemblyzer dependencies are not installed")
        logger.info("Install with: pip install resemblyzer torch librosa soundfile webrtcvad")
        return False
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        traceback.print_exc()
        return False


def test_environment():
    """Test environment configuration."""
    logger.info("Testing environment configuration...")
    
    env_vars = [
        'EMBEDDING_PROCESSOR_TYPE',
        'VOICE_EMBEDDING_DIMENSIONS',
        'LOG_LEVEL'
    ]
    
    for var in env_vars:
        value = os.getenv(var, 'NOT_SET')
        logger.info(f"{var}: {value}")
    
    # Test Python environment
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Test imports
    logger.info("Testing imports...")
    if NUMPY_AVAILABLE:
        logger.info(f"NumPy {np.__version__}")
    else:
        logger.error("NumPy not available")
    
    if TORCH_AVAILABLE:
        logger.info(f"PyTorch {torch.__version__}")
    else:
        logger.info("PyTorch not available (expected if not installed)")
    
    if LIBROSA_AVAILABLE:
        logger.info(f"Librosa {librosa.__version__}")
    else:
        logger.info("Librosa not available (expected if not installed)")
    
    if RESEMBLYZER_AVAILABLE:
        logger.info(f"Resemblyzer available")
    else:
        logger.info("Resemblyzer not available (expected if not installed)")


def main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Voice Gateway - Resemblyzer Integration Test")
    logger.info("=" * 60)
    
    # Test environment
    test_environment()
    logger.info("-" * 60)
    
    # Test audio processor
    success = test_audio_processor()
    
    logger.info("-" * 60)
    if success:
        logger.info("All tests passed!")
    else:
        logger.error("Some tests failed!")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
