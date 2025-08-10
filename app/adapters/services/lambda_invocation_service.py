"""
AWS Lambda invocation service adapter.
Implements Lambda invocation using boto3 following Clean Architecture.
"""
import json
import base64
import logging
import uuid
from typing import Dict, Any, Optional
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.core.ports.lambda_invocation import (
    LambdaInvocationPort, 
    LambdaInvocationError, 
    AuthenticationProcessingError
)
from app.infrastructure.config.infrastructure_settings import infra_settings

logger = logging.getLogger(__name__)


class AWSLambdaInvocationService(LambdaInvocationPort):
    """
    AWS Lambda invocation service implementation.
    
    Provides Lambda function invocation using boto3 with proper error handling,
    retries, and response processing.
    """
    
    def __init__(self):
        """Initialize AWS Lambda client."""
        self._lambda_client: Optional[boto3.client] = None
        self.voice_auth_function_name = "voice-authentication-processor"
        
    @property
    def lambda_client(self) -> boto3.client:
        """Get or create Lambda client."""
        if self._lambda_client is None:
            self._lambda_client = boto3.client(
                'lambda',
                region_name=infra_settings.aws_region
            )
        return self._lambda_client
    
    async def invoke_voice_authentication(
        self,
        user_id: UUID,
        audio_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke voice authentication Lambda function with stream processing.
        
        Uses direct Lambda invocation for real-time authentication without S3 storage.
        """
        request_id = str(uuid.uuid4())
        
        logger.info("Invoking voice authentication Lambda", extra={
            "user_id": str(user_id),
            "request_id": request_id,
            "audio_size_bytes": len(audio_data),
            "function_name": self.voice_auth_function_name
        })
        
        try:
            # Prepare payload for stream invocation
            payload = {
                "invocation_type": "stream",
                "user_id": str(user_id),
                "audio_data": base64.b64encode(audio_data).decode('utf-8'),
                "metadata": metadata or {},
                "request_id": request_id
            }
            
            # Add FastAPI source metadata
            payload["metadata"].update({
                "source": "fastapi",
                "invocation_type": "stream",
                "request_id": request_id
            })
            
            # Invoke Lambda function
            response = await self.invoke_async(
                function_name=self.voice_auth_function_name,
                payload=payload,
                invocation_type="RequestResponse"
            )
            
            # Process and validate response
            return self._process_voice_auth_response(response, user_id, request_id)
            
        except AuthenticationProcessingError:
            # Re-raise authentication errors as-is
            raise
        except Exception as e:
            logger.error("Voice authentication Lambda invocation failed", extra={
                "user_id": str(user_id),
                "request_id": request_id,
                "error": str(e),
                "function_name": self.voice_auth_function_name
            })
            raise LambdaInvocationError(
                f"Failed to invoke voice authentication Lambda: {str(e)}",
                function_name=self.voice_auth_function_name,
                error_details={
                    "user_id": str(user_id),
                    "request_id": request_id,
                    "original_error": str(e)
                }
            )
    
    async def invoke_async(
        self,
        function_name: str,
        payload: Dict[str, Any],
        invocation_type: str = "RequestResponse"
    ) -> Dict[str, Any]:
        """
        Generic async Lambda function invocation.
        """
        try:
            logger.debug("Invoking Lambda function", extra={
                "function_name": function_name,
                "invocation_type": invocation_type,
                "payload_size": len(json.dumps(payload))
            })
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,
                Payload=json.dumps(payload)
            )
            
            # Read and parse response
            response_payload = response['Payload'].read()
            
            if response.get('StatusCode') != 200:
                raise LambdaInvocationError(
                    f"Lambda invocation failed with status {response.get('StatusCode')}",
                    function_name=function_name,
                    error_details={
                        "status_code": response.get('StatusCode'),
                        "response": response_payload.decode('utf-8') if response_payload else None
                    }
                )
            
            # Parse JSON response
            if response_payload:
                result = json.loads(response_payload.decode('utf-8'))
                
                logger.debug("Lambda function invoked successfully", extra={
                    "function_name": function_name,
                    "response_status": result.get('statusCode', 'unknown')
                })
                
                return result
            else:
                raise LambdaInvocationError(
                    "Empty response from Lambda function",
                    function_name=function_name
                )
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            logger.error("AWS Lambda ClientError", extra={
                "function_name": function_name,
                "error_code": error_code,
                "error_message": error_message
            })
            
            raise LambdaInvocationError(
                f"AWS Lambda error: {error_message}",
                function_name=function_name,
                error_details={
                    "error_code": error_code,
                    "aws_error": error_message
                }
            )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse Lambda response JSON", extra={
                "function_name": function_name,
                "error": str(e)
            })
            raise LambdaInvocationError(
                f"Invalid JSON response from Lambda: {str(e)}",
                function_name=function_name
            )
    
    def _process_voice_auth_response(
        self, 
        response: Dict[str, Any], 
        user_id: UUID, 
        request_id: str
    ) -> Dict[str, Any]:
        """
        Process and validate voice authentication Lambda response.
        """
        try:
            # Extract status code and body
            status_code = response.get('statusCode', 500)
            body = response.get('body', {})
            
            if status_code != 200:
                error_message = body.get('error_message', 'Authentication processing failed')
                error_details = body.get('error_details', {})
                
                logger.warning("Voice authentication failed", extra={
                    "user_id": str(user_id),
                    "request_id": request_id,
                    "status_code": status_code,
                    "error_message": error_message
                })
                
                raise AuthenticationProcessingError(
                    error_message,
                    user_id=str(user_id),
                    error_details=error_details
                )
            
            # Validate required fields in successful response
            required_fields = [
                'authentication_successful', 
                'confidence_score', 
                'processing_time_ms'
            ]
            
            for field in required_fields:
                if field not in body:
                    raise AuthenticationProcessingError(
                        f"Missing required field in Lambda response: {field}",
                        user_id=str(user_id),
                        error_details={"missing_field": field, "response_body": body}
                    )
            
            # Add metadata
            body['user_id'] = str(user_id)
            body['request_id'] = request_id
            
            logger.info("Voice authentication Lambda response processed", extra={
                "user_id": str(user_id),
                "request_id": request_id,
                "authentication_successful": body['authentication_successful'],
                "confidence_score": body['confidence_score']
            })
            
            return body
            
        except AuthenticationProcessingError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            logger.error("Failed to process voice authentication response", extra={
                "user_id": str(user_id),
                "request_id": request_id,
                "error": str(e),
                "response": response
            })
            
            raise AuthenticationProcessingError(
                f"Failed to process Lambda response: {str(e)}",
                user_id=str(user_id),
                error_details={"original_error": str(e), "response": response}
            )
