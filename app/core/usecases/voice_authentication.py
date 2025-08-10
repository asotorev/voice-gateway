"""
Voice authentication use case.
Orchestrates voice authentication workflow following Clean Architecture.
"""
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.ports.lambda_invocation import LambdaInvocationPort, AuthenticationProcessingError
from app.core.ports.user_repository import UserRepositoryPort


class VoiceAuthenticationUseCase:
    """
    Use case for voice authentication workflow.
    
    Orchestrates the complete voice authentication process including
    user validation, Lambda invocation, and result processing.
    """
    
    def __init__(
        self,
        lambda_invocation: LambdaInvocationPort,
        user_repository: UserRepositoryPort
    ):
        """
        Initialize voice authentication use case.
        
        Args:
            lambda_invocation: Lambda invocation service
            user_repository: User repository for validation
        """
        self.lambda_invocation = lambda_invocation
        self.user_repository = user_repository
    
    async def authenticate_user_voice(
        self,
        user_id: UUID,
        audio_data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform voice authentication for a user.
        
        Args:
            user_id: User identifier
            audio_data: Raw audio bytes for authentication
            metadata: Additional metadata for processing
            
        Returns:
            Authentication results with detailed validation information
            
        Raises:
            ValueError: If user not found or not ready for voice authentication
            AuthenticationProcessingError: If authentication processing fails
        """
        # Use case orchestration - no logging in domain layer
        
        try:
            # Step 1: Validate user exists and is ready for voice authentication
            await self._validate_user_for_authentication(user_id)
            
            # Step 2: Prepare metadata
            processing_metadata = metadata or {}
            processing_metadata.update({
                "use_case": "voice_authentication",
                "source": "fastapi_endpoint"
            })
            
            # Step 3: Invoke voice authentication Lambda
            
            auth_result = await self.lambda_invocation.invoke_voice_authentication(
                user_id=user_id,
                audio_data=audio_data,
                metadata=processing_metadata
            )
            
            # Step 4: Process and enrich results
            enriched_result = await self._enrich_authentication_result(
                user_id, auth_result
            )
            
            # Voice authentication workflow completed
            
            return enriched_result
            
        except ValueError:
            # Re-raise validation errors
            raise
        except AuthenticationProcessingError:
            # Re-raise processing errors
            raise
        except Exception as e:
            # Re-raise as domain-specific error
            raise AuthenticationProcessingError(
                f"Voice authentication workflow failed: {str(e)}",
                user_id=str(user_id),
                error_details={"original_error": str(e)}
            )
    
    async def _validate_user_for_authentication(self, user_id: UUID) -> None:
        """
        Validate that user exists and is ready for voice authentication.
        
        Args:
            user_id: User identifier to validate
            
        Raises:
            ValueError: If user not found or not ready for authentication
        """
        # Check if user exists
        user = await self.user_repository.get_user(str(user_id))
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if user has voice password
        if not user.get('password_hash'):
            raise ValueError(f"User {user_id} does not have a voice password")
        
        # Check if user has completed voice registration
        voice_embeddings = await self.user_repository.get_user_embeddings(str(user_id))
        if not voice_embeddings or len(voice_embeddings) < 3:
            raise ValueError(
                f"User {user_id} has not completed voice registration. "
                f"Found {len(voice_embeddings) if voice_embeddings else 0}/3 voice samples."
            )
        
        # User validation completed successfully
    
    async def _enrich_authentication_result(
        self, 
        user_id: UUID, 
        auth_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enrich authentication result with additional user context.
        
        Args:
            user_id: User identifier
            auth_result: Raw authentication result from Lambda
            
        Returns:
            Enriched authentication result
        """
        try:
            # Get user profile for enrichment
            user = await self.user_repository.get_user(str(user_id))
            
            # Add user context
            auth_result['user_context'] = {
                'user_id': str(user_id),
                'user_name': user.get('name') if user else None,
                'user_email': user.get('email') if user else None
            }
            
            # Add authentication method details
            auth_result['authentication_method'] = 'voice_dual_validation'
            auth_result['validation_methods'] = ['whisper_transcription', 'voice_embedding_biometric']
            
            return auth_result
            
        except Exception as e:
            # Return original result if enrichment fails - no logging in domain layer
            return auth_result
