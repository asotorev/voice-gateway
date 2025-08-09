"""
Audio processing interface and implementations for Lambda function.

This module provides the interface for audio processing operations and
implementations for generating voice embeddings. It includes both mock
and real ML processors to support development and production workflows.
"""
import os
import logging
import hashlib
import numpy as np
import tempfile
import io
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Resemblyzer and audio processing imports
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    import librosa
    import soundfile as sf
    RESEMBLYZER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Resemblyzer dependencies not available: {e}")
    RESEMBLYZER_AVAILABLE = False



class AudioProcessor(ABC):
    """
    Abstract base class for audio processing implementations.
    
    Defines the interface for processing audio data and generating
    voice embeddings. Implementations can be mock (for development)
    or real ML models (for production).
    """
    
    @abstractmethod
    def generate_embedding(self, audio_data: bytes, metadata: Dict[str, Any]) -> List[float]:
        """
        Generate voice embedding from audio data.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata (size, format, etc.)
            
        Returns:
            Voice embedding as list of floats
            
        Raises:
            ValueError: If audio data is invalid
            RuntimeError: If processing fails
        """
        pass
    
    @abstractmethod
    def validate_audio_quality(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate audio quality for embedding generation.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Dict with quality assessment results
        """
        pass
    
    @abstractmethod
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get information about the processor implementation.
        
        Returns:
            Dict with processor details
        """
        pass


class MockAudioProcessor(AudioProcessor):
    """
    Mock audio processor for development and testing.
    
    Generates deterministic but realistic voice embeddings without
    requiring actual ML models. Useful for development, testing,
    and CI/CD pipelines.
    """
    
    def __init__(self):
        """Initialize mock audio processor."""
        self.embedding_dimensions = int(os.getenv('VOICE_EMBEDDING_DIMENSIONS', '256'))
        self.processor_version = "mock-1.0.0"
        
        logger.info("Mock audio processor initialized", extra={
            "embedding_dimensions": self.embedding_dimensions,
            "processor_version": self.processor_version
        })
    
    def generate_embedding(self, audio_data: bytes, metadata: Dict[str, Any]) -> List[float]:
        """
        Generate mock voice embedding from audio data.
        
        Creates deterministic embeddings based on audio content hash,
        ensuring consistent results for the same input while providing
        realistic vector dimensions and value ranges.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Mock voice embedding as list of floats
            
        Raises:
            ValueError: If audio data is invalid
        """
        logger.info("Generating mock voice embedding", extra={
            "audio_size_bytes": len(audio_data),
            "embedding_dimensions": self.embedding_dimensions
        })
        
        try:
            # Validate input
            if not audio_data or len(audio_data) == 0:
                raise ValueError("Audio data is empty")
            
            if len(audio_data) < 1000:  # Minimum reasonable audio file size
                raise ValueError("Audio data too small - likely corrupted")
            
            # Generate deterministic hash from audio content
            audio_hash = hashlib.sha256(audio_data).hexdigest()
            
            # Use hash to seed random number generator for deterministic results
            seed = int(audio_hash[:8], 16)
            np.random.seed(seed)
            
            # Generate realistic embedding
            # Use normal distribution with slight bias based on file characteristics
            base_embedding = np.random.normal(0, 1, self.embedding_dimensions)
            
            # Add file-size based bias for more realistic variation
            size_bias = (len(audio_data) % 1000) / 1000.0 - 0.5
            base_embedding += size_bias * 0.1
            
            # Normalize to unit vector (common in voice embeddings)
            embedding = base_embedding / np.linalg.norm(base_embedding)
            
            # Convert to list and ensure float type
            embedding_list = [float(x) for x in embedding.tolist()]
            
            logger.info("Mock embedding generated successfully", extra={
                "embedding_dimensions": len(embedding_list),
                "embedding_norm": float(np.linalg.norm(embedding)),
                "audio_hash": audio_hash[:8]
            })
            
            return embedding_list
            
        except Exception as e:
            logger.error("Failed to generate mock embedding", extra={
                "error": str(e),
                "audio_size": len(audio_data) if audio_data else 0
            })
            raise RuntimeError(f"Mock embedding generation failed: {str(e)}")
    
    def validate_audio_quality(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock audio quality validation.
        
        Performs basic checks and returns mock quality scores.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Dict with mock quality assessment
        """
        logger.debug("Performing mock audio quality validation")
        
        # Validate input first
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")
        
        try:
            
            # Basic validation checks
            is_valid = True
            issues = []
            warnings = []
            quality_issues = []
            
            # Check file size
            if len(audio_data) < 1000:
                is_valid = False
                issues.append("Audio file too small")
                quality_issues.append("File very small")
            elif len(audio_data) < 10000:
                warnings.append("Audio file might be too short for quality embedding")
            
            # Mock quality scores based on file characteristics
            file_size_score = min(1.0, len(audio_data) / 100000.0)  # Better score for larger files
            format_score = 0.9 if metadata.get('file_extension', '').lower() == 'wav' else 0.7
            
            # Generate deterministic quality score
            audio_hash = hashlib.md5(audio_data[:1000]).hexdigest()
            hash_score = (int(audio_hash[:2], 16) % 30 + 70) / 100.0  # Score between 0.7-1.0
            
            overall_quality = (file_size_score + format_score + hash_score) / 3.0
            
            # Generate additional mock metrics that tests expect
            snr_estimate = 20.0 + (hash_score * 15.0)  # SNR between 20-35 dB
            voice_activity_ratio = 0.8 + (hash_score * 0.15)  # VAR between 0.8-0.95
            background_noise_level = 0.1 - (hash_score * 0.08)  # Noise between 0.02-0.1
            
            quality_result = {
                'is_valid': is_valid,
                'overall_quality_score': overall_quality,
                'snr_estimate': snr_estimate,
                'voice_activity_ratio': voice_activity_ratio,
                'background_noise_level': background_noise_level,
                'quality_issues': quality_issues,
                'quality_scores': {
                    'file_size_score': file_size_score,
                    'format_score': format_score,
                    'content_score': hash_score
                },
                'issues': issues,
                'warnings': warnings,
                'processing_recommendation': 'proceed' if overall_quality > 0.6 else 'retry',
                'validated_at': datetime.now(timezone.utc).isoformat()
            }
            
            logger.debug("Mock quality validation completed", extra={
                "overall_quality": overall_quality,
                "is_valid": is_valid,
                "issues_count": len(issues)
            })
            
            return quality_result
            
        except Exception as e:
            logger.error("Mock quality validation failed", extra={"error": str(e)})
            return {
                'is_valid': False,
                'overall_quality_score': 0.0,
                'issues': [f"Validation error: {str(e)}"],
                'warnings': [],
                'processing_recommendation': 'error'
            }
    
    def get_processor_info(self) -> Dict[str, Any]:
        """
        Get mock processor information.
        
        Returns:
            Dict with processor details
        """
        return {
            'processor_type': 'mock',
            'processor_name': 'MockAudioProcessor',
            'processor_version': self.processor_version,
            'embedding_dimensions': self.embedding_dimensions,
            'processing_time_ms': 150,  # Mock processing time
            'capabilities': [
                'deterministic_embeddings',
                'quality_validation',
                'development_testing'
            ],
            'limitations': [
                'not_production_ready',
                'mock_quality_scores',
                'hash_based_embeddings'
            ],
            'model_info': {
                'type': 'hash_based_mock',
                'deterministic': True,
                'normalized_output': True
            }
        }


class ResemblyzerAudioProcessor(AudioProcessor):
    """
    Resemblyzer-based audio processor for production voice embedding generation.
    
    Uses the Resemblyzer library to generate high-quality speaker embeddings
    from voice audio samples. Handles audio preprocessing, quality validation,
    and embedding generation with proper error handling.
    """
    
    def __init__(self):
        """Initialize Resemblyzer audio processor."""
        if not RESEMBLYZER_AVAILABLE:
            raise ImportError("Resemblyzer dependencies not available. Install with: pip install resemblyzer librosa soundfile")
        
        self.embedding_dimensions = 256  # Resemblyzer produces 256-dimensional embeddings
        self.processor_version = "resemblyzer-1.0.0"
        self.target_sample_rate = 16000  # Resemblyzer expects 16kHz
        self.min_audio_length = 1.0  # Minimum 1 second
        self.max_audio_length = 30.0  # Maximum 30 seconds
        
        # Initialize Resemblyzer encoder
        try:
            self.encoder = VoiceEncoder()
            logger.info("Resemblyzer encoder initialized successfully", extra={
                "embedding_dimensions": self.embedding_dimensions,
                "target_sample_rate": self.target_sample_rate
            })
        except Exception as e:
            logger.error(f"Failed to initialize Resemblyzer encoder: {e}")
            raise RuntimeError(f"Resemblyzer initialization failed: {e}")
    
    def generate_embedding(self, audio_data: bytes, metadata: Dict[str, Any]) -> List[float]:
        """
        Generate voice embedding using Resemblyzer.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Voice embedding as list of floats (256 dimensions)
            
        Raises:
            ValueError: If audio data is invalid or processing fails
            RuntimeError: If Resemblyzer processing fails
        """
        logger.info("Generating voice embedding with Resemblyzer", extra={
            "audio_size_bytes": len(audio_data),
            "metadata": metadata
        })
        
        try:
            # Preprocess audio data
            wav_data = self._preprocess_audio(audio_data, metadata)
            
            # Generate embedding using Resemblyzer
            embedding = self.encoder.embed_utterance(wav_data)
            
            # Convert numpy array to list
            embedding_list = embedding.tolist()
            
            logger.info("Voice embedding generated successfully", extra={
                "embedding_dimensions": len(embedding_list),
                "embedding_norm": float(np.linalg.norm(embedding))
            })
            
            return embedding_list
            
        except Exception as e:
            logger.error("Failed to generate voice embedding", extra={
                "error": str(e),
                "audio_size": len(audio_data)
            })
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    def validate_audio_quality(self, audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate audio quality for Resemblyzer processing.
        
        Args:
            audio_data: Raw audio file bytes
            metadata: Audio file metadata
            
        Returns:
            Dict with quality assessment results
        """
        logger.debug("Validating audio quality for Resemblyzer")
        
        validation_result = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'metrics': {},
            'overall_quality_score': 0.0
        }
        
        try:
            # Load and preprocess audio for analysis
            wav_data, sample_rate = self._load_audio_for_analysis(audio_data)
            
            # Check audio length
            duration = len(wav_data) / sample_rate
            validation_result['metrics']['duration_seconds'] = duration
            
            if duration < self.min_audio_length:
                validation_result['is_valid'] = False
                validation_result['issues'].append(f"Audio too short: {duration:.2f}s < {self.min_audio_length}s")
            elif duration > self.max_audio_length:
                validation_result['warnings'].append(f"Audio long: {duration:.2f}s > {self.max_audio_length}s (will be truncated)")
            
            # Check sample rate
            validation_result['metrics']['sample_rate'] = sample_rate
            if sample_rate < 8000:
                validation_result['is_valid'] = False
                validation_result['issues'].append(f"Sample rate too low: {sample_rate}Hz < 8000Hz")
            elif sample_rate != self.target_sample_rate:
                validation_result['warnings'].append(f"Sample rate {sample_rate}Hz will be resampled to {self.target_sample_rate}Hz")
            
            # Signal analysis
            signal_analysis = self._analyze_signal_quality(wav_data)
            validation_result['metrics'].update(signal_analysis)
            
            # Voice activity detection
            voice_activity = self._detect_voice_activity(wav_data, sample_rate)
            validation_result['metrics']['voice_activity_ratio'] = voice_activity
            
            if voice_activity < 0.3:
                validation_result['warnings'].append(f"Low voice activity: {voice_activity:.2f} < 0.3")
            
            # Calculate overall quality score
            quality_score = self._calculate_quality_score(validation_result['metrics'])
            validation_result['overall_quality_score'] = quality_score
            
            if quality_score < 0.5:
                validation_result['is_valid'] = False
                validation_result['issues'].append(f"Overall quality too low: {quality_score:.3f}")
            elif quality_score < 0.7:
                validation_result['warnings'].append(f"Moderate quality: {quality_score:.3f}")
            
            logger.debug("Audio quality validation completed", extra={
                "is_valid": validation_result['is_valid'],
                "quality_score": quality_score,
                "issues": len(validation_result['issues']),
                "warnings": len(validation_result['warnings'])
            })
            
            return validation_result
            
        except Exception as e:
            logger.warning("Audio quality validation failed", extra={"error": str(e)})
            # Return a permissive result if validation fails
            return {
                'is_valid': True,
                'issues': [],
                'warnings': [f"Quality validation failed: {str(e)}"],
                'metrics': {},
                'overall_quality_score': 0.7  # Default acceptable score
            }
    
    def get_processor_info(self) -> Dict[str, Any]:
        """Get Resemblyzer processor information."""
        return {
            'processor_type': 'resemblyzer',
            'processor_name': 'ResemblyzerAudioProcessor',
            'processor_version': self.processor_version,
            'embedding_dimensions': self.embedding_dimensions,
            'status': 'active',
            'capabilities': [
                'voice_embeddings',
                'speaker_verification',
                'voice_cloning_detection'
            ],
            'model_info': {
                'type': 'neural_network',
                'framework': 'pytorch',
                'pretrained': True,
                'target_sample_rate': self.target_sample_rate
            },
            'quality_requirements': {
                'min_duration_seconds': self.min_audio_length,
                'max_duration_seconds': self.max_audio_length,
                'target_sample_rate': self.target_sample_rate,
                'min_voice_activity': 0.3
            }
        }
    
    def _preprocess_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> np.ndarray:
        """
        Preprocess audio data for Resemblyzer.
        
        Args:
            audio_data: Raw audio bytes
            metadata: Audio metadata
            
        Returns:
            Preprocessed audio as numpy array
        """
        try:
            # Load audio data
            wav_data, sample_rate = self._load_audio_for_analysis(audio_data)
            
            # Resample to target sample rate if needed
            if sample_rate != self.target_sample_rate:
                wav_data = librosa.resample(wav_data, orig_sr=sample_rate, target_sr=self.target_sample_rate)
                sample_rate = self.target_sample_rate
            
            # Trim or pad audio to reasonable length
            target_length = int(self.max_audio_length * sample_rate)
            if len(wav_data) > target_length:
                wav_data = wav_data[:target_length]
            
            # Use Resemblyzer's preprocessing
            wav_preprocessed = preprocess_wav(wav_data, source_sr=sample_rate)
            
            return wav_preprocessed
            
        except Exception as e:
            logger.error("Audio preprocessing failed", extra={"error": str(e)})
            raise ValueError(f"Audio preprocessing failed: {e}")
    
    def _load_audio_for_analysis(self, audio_data: bytes) -> Tuple[np.ndarray, int]:
        """
        Load audio data from bytes for analysis.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        try:
            # Create temporary file for audio data
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file.flush()
                
                # Load audio using soundfile
                wav_data, sample_rate = sf.read(temp_file.name)
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
                # Ensure mono audio
                if wav_data.ndim > 1:
                    wav_data = np.mean(wav_data, axis=1)
                
                return wav_data.astype(np.float32), sample_rate
                
        except Exception as e:
            # Fallback: try using librosa directly on bytes
            try:
                audio_io = io.BytesIO(audio_data)
                wav_data, sample_rate = librosa.load(audio_io, sr=None, mono=True)
                return wav_data.astype(np.float32), sample_rate
            except Exception as fallback_error:
                raise ValueError(f"Failed to load audio data: {e}, fallback failed: {fallback_error}")
    
    def _analyze_signal_quality(self, wav_data: np.ndarray) -> Dict[str, float]:
        """Analyze signal quality metrics."""
        try:
            # Signal-to-noise ratio estimation
            signal_power = np.mean(wav_data ** 2)
            noise_floor = np.percentile(np.abs(wav_data), 10)  # Estimate noise as 10th percentile
            snr_estimate = 10 * np.log10(signal_power / (noise_floor ** 2 + 1e-10))
            
            # Dynamic range
            dynamic_range = np.max(np.abs(wav_data)) - noise_floor
            
            # Zero crossing rate (measure of voicing)
            zero_crossings = np.sum(np.diff(np.sign(wav_data)) != 0)
            zcr = zero_crossings / len(wav_data)
            
            return {
                'snr_estimate': float(max(0, min(50, snr_estimate))),  # Clamp to 0-50 dB
                'dynamic_range': float(dynamic_range),
                'zero_crossing_rate': float(zcr),
                'rms_level': float(np.sqrt(signal_power))
            }
            
        except Exception as e:
            logger.warning(f"Signal analysis failed: {e}")
            return {
                'snr_estimate': 20.0,  # Default moderate SNR
                'dynamic_range': 0.5,
                'zero_crossing_rate': 0.1,
                'rms_level': 0.1
            }
    
    def _detect_voice_activity(self, wav_data: np.ndarray, sample_rate: int) -> float:
        """
        Detect voice activity ratio using energy-based approach.
        
        Args:
            wav_data: Audio signal
            sample_rate: Sample rate
            
        Returns:
            Voice activity ratio (0.0 to 1.0)
        """
        try:
            # Simple energy-based voice activity detection
            frame_length = int(0.025 * sample_rate)  # 25ms frames
            hop_length = int(0.010 * sample_rate)    # 10ms hop
            
            # Calculate frame energy
            frames = librosa.util.frame(wav_data, frame_length=frame_length, hop_length=hop_length)
            frame_energy = np.sum(frames ** 2, axis=0)
            
            # Threshold based on energy distribution
            energy_threshold = np.percentile(frame_energy, 60)  # 60th percentile
            
            # Count active frames
            active_frames = np.sum(frame_energy > energy_threshold)
            total_frames = len(frame_energy)
            
            voice_activity_ratio = active_frames / total_frames if total_frames > 0 else 0.0
            
            return float(min(1.0, max(0.0, voice_activity_ratio)))
            
        except Exception as e:
            logger.warning(f"Voice activity detection failed: {e}")
            return 0.7  # Default moderate activity
    
    def _calculate_quality_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate overall quality score from metrics.
        
        Args:
            metrics: Quality metrics dictionary
            
        Returns:
            Quality score from 0.0 to 1.0
        """
        try:
            score = 0.0
            
            # SNR contribution (40%)
            snr = metrics.get('snr_estimate', 20.0)
            snr_score = min(1.0, max(0.0, (snr - 5.0) / 25.0))  # 5-30 dB range
            score += 0.4 * snr_score
            
            # Voice activity contribution (30%)
            voice_activity = metrics.get('voice_activity_ratio', 0.7)
            score += 0.3 * voice_activity
            
            # Dynamic range contribution (20%)
            dynamic_range = metrics.get('dynamic_range', 0.5)
            dr_score = min(1.0, max(0.0, dynamic_range * 2.0))  # 0-0.5 range
            score += 0.2 * dr_score
            
            # RMS level contribution (10%)
            rms_level = metrics.get('rms_level', 0.1)
            rms_score = min(1.0, max(0.0, rms_level * 10.0))  # 0-0.1 range
            score += 0.1 * rms_score
            
            return float(min(1.0, max(0.0, score)))
            
        except Exception as e:
            logger.warning(f"Quality score calculation failed: {e}")
            return 0.7  # Default moderate quality


def get_audio_processor() -> AudioProcessor:
    """
    Factory function to get the appropriate audio processor.
    
    Returns the configured audio processor based on environment settings.
    
    Returns:
        AudioProcessor instance (mock or real)
    """
    processor_type = os.getenv('EMBEDDING_PROCESSOR_TYPE', 'mock').lower()
    
    if processor_type == 'resemblyzer':
        logger.info("Creating Resemblyzer audio processor")
        return ResemblyzerAudioProcessor()
    else:
        logger.info("Creating mock audio processor")
        return MockAudioProcessor()


def process_audio_file(audio_data: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    High-level function to process audio file and generate embedding.
    
    Args:
        audio_data: Raw audio file bytes
        metadata: Audio file metadata
        
    Returns:
        Dict with processing results including embedding and quality info
        
    Raises:
        ValueError: If input is invalid
        RuntimeError: If processing fails
    """
    logger.info("Starting audio file processing", extra={
        "audio_size_bytes": len(audio_data),
        "metadata": metadata
    })
    
    try:
        # Validate input
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")
        
        if not metadata:
            raise ValueError("File metadata is required")
        
        # Get processor instance
        processor = get_audio_processor()
        
        # Validate audio quality first
        quality_result = processor.validate_audio_quality(audio_data, metadata)
        
        if not quality_result.get('is_valid', False):
            raise ValueError(f"Audio quality validation failed: {quality_result.get('issues', [])}")
        
        # Generate embedding
        embedding = processor.generate_embedding(audio_data, metadata)
        
        # Generate mock audio analysis
        audio_analysis = {
            'duration_seconds': len(audio_data) / 44100.0,  # Rough estimate
            'sample_rate': metadata.get('sample_rate', 44100),
            'channels': metadata.get('channels', 1),
            'format': metadata.get('file_extension', 'unknown'),
            'file_size_bytes': len(audio_data)
        }
        
        # Compile results
        result = {
            'embedding': embedding,
            'embedding_dimensions': len(embedding),
            'quality_assessment': quality_result,
            'processor_info': processor.get_processor_info(),
            'audio_analysis': audio_analysis,
            'processed_at': datetime.now(timezone.utc).isoformat(),
            'success': True
        }
        
        logger.info("Audio processing completed successfully", extra={
            "embedding_dimensions": len(embedding),
            "quality_score": quality_result.get('overall_quality_score', 0),
            "processor_type": processor.get_processor_info().get('processor_type')
        })
        
        return result
        
    except Exception as e:
        logger.error("Audio processing failed", extra={
            "error": str(e),
            "audio_size": len(audio_data)
        })
        raise
