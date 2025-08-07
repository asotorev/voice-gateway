"""
Audio Embedding Processor Lambda Function.

This module contains the serverless audio processing pipeline for generating
voice embeddings from uploaded audio files. The Lambda function is triggered
by S3 events when users upload voice samples during registration.

Architecture:
- Event-driven processing triggered by S3 ObjectCreated events
- Serverless compute for cost-effective ML workload handling
- Automatic scaling based on upload volume
- Separation of API concerns from compute-intensive processing

The processor handles:
1. S3 event parsing and validation
2. Audio file download and preprocessing
3. ML-based embedding generation
4. User registration status tracking
5. DynamoDB updates with computed embeddings
"""

__version__ = "1.0.0"
__author__ = "Voice Gateway Team"
