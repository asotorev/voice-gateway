"""
Lambda invocation port for Clean Architecture.
Defines interface for AWS Lambda function invocation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID


class LambdaInvocationPort(ABC):
    """
    Port for AWS Lambda function invocation.
    
    Provides abstraction for invoking Lambda functions following Clean Architecture
    principles with proper error handling and response management.
    """
    
    @abstractmethod
    async def invoke_voice_authentication(
        self,
        user_id: UUID,
        audio_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke voice authentication Lambda function.
        
        Args:
            user_id: User identifier for authentication
            audio_data: Raw audio bytes to process
            metadata: Additional metadata for processing
            
        Returns:
            Lambda function response with authentication results
            
        Raises:
            LambdaInvocationError: If Lambda invocation fails
            AuthenticationProcessingError: If authentication processing fails
        """
        pass
    
    @abstractmethod
    async def invoke_async(
        self,
        function_name: str,
        payload: Dict[str, Any],
        invocation_type: str = "RequestResponse"
    ) -> Dict[str, Any]:
        """
        Generic async Lambda function invocation.
        
        Args:
            function_name: Name of the Lambda function to invoke
            payload: Payload to send to the Lambda function
            invocation_type: Lambda invocation type ("Event" or "RequestResponse")
            
        Returns:
            Lambda function response
            
        Raises:
            LambdaInvocationError: If Lambda invocation fails
        """
        pass


class LambdaInvocationError(Exception):
    """Exception raised when Lambda invocation fails."""
    
    def __init__(self, message: str, function_name: str, error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.function_name = function_name
        self.error_details = error_details or {}


class AuthenticationProcessingError(Exception):
    """Exception raised when authentication processing fails in Lambda."""
    
    def __init__(self, message: str, user_id: str, error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.user_id = user_id
        self.error_details = error_details or {}
