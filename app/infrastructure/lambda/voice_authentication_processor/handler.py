"""
Lambda handler for voice authentication processing from S3 events.

This module serves as the entry point for the Lambda function that processes
voice authentication requests using Clean Architecture principles.

Event Flow:
1. S3 uploads trigger Lambda with ObjectCreated event
2. Handler validates and parses the S3 event  
3. Delegates to presentation layer for authentication processing
"""

# Delegate to the new Clean Architecture handler
from presentation.lambda_handler import lambda_handler
