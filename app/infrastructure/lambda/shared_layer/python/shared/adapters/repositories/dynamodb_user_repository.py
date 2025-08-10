"""
DynamoDB user repository implementation.

This module provides the DynamoDB-based implementation of the UserRepositoryPort
interface, following Clean Architecture principles with dependency inversion.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError

from ...core.ports.user_repository import UserRepositoryPort
from ...core.models.voice_embedding import VoiceEmbedding
from ...infrastructure.aws.aws_config import aws_config_manager

logger = logging.getLogger(__name__)


class DynamoDBUserRepository(UserRepositoryPort):
    """
    DynamoDB implementation of the user repository.
    
    Handles user record management, voice embedding storage, and registration
    completion tracking with proper error handling and atomic operations.
    """
    
    def __init__(self):
        """Initialize DynamoDB user repository."""
        self.dynamodb_resource = aws_config_manager.dynamodb_resource
        self.table_name = aws_config_manager.get_users_table_name()
        self.table = self.dynamodb_resource.Table(self.table_name)
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        
        logger.info("DynamoDB user repository initialized", extra={
            "table": self.table_name,
            "required_samples": self.required_samples
        })
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user record by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            User record dict or None if not found
        """
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' in response:
                user = response['Item']
                logger.debug("User retrieved successfully", extra={
                    "user_id": user_id,
                    "has_voice_embeddings": 'voice_embeddings' in user
                })
                return user
            else:
                logger.info("User not found", extra={"user_id": user_id})
                return None
                
        except ClientError as e:
            aws_config_manager.handle_aws_error(e, "get_user", user_id)
            raise
        except Exception as e:
            logger.error("Failed to get user", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    async def add_voice_embedding(
        self,
        user_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a voice embedding to user record.
        
        Args:
            user_id: User identifier
            embedding: Voice embedding vector
            metadata: Embedding metadata
            
        Returns:
            Updated user record information
        """
        logger.info("Adding voice embedding to user", extra={
            "user_id": user_id,
            "embedding_dimensions": len(embedding),
            "audio_file": metadata.get('file_name', 'unknown')
        })
        
        try:
            # Validate embedding
            if not embedding or not isinstance(embedding, list):
                raise ValueError("Invalid embedding: must be non-empty list")
            
            if not all(isinstance(x, (int, float)) for x in embedding):
                raise ValueError("Invalid embedding: all values must be numeric")
            
            # Get current user record
            user = await self.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Prepare embedding entry
            embedding_entry = {
                'embedding': embedding,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'audio_metadata': {
                    'file_name': metadata.get('file_name', ''),
                    'file_size': metadata.get('size_bytes', 0),
                    'quality_score': metadata.get('quality_score', 0.0),
                    'processor_type': metadata.get('processor_type', 'unknown'),
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Get current embeddings or initialize empty list
            current_embeddings = user.get('voice_embeddings', [])
            
            # Add new embedding
            current_embeddings.append(embedding_entry)
            
            # Calculate new embedding count
            new_embedding_count = len(current_embeddings)
            
            # Check if registration is complete
            is_complete = new_embedding_count >= self.required_samples
            
            # Update user record atomically with embedding count
            update_expression = "SET voice_embeddings = :embeddings, voice_embeddings_count = :count, updated_at = :updated_at"
            expression_values = {
                ':embeddings': current_embeddings,
                ':count': new_embedding_count,
                ':updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Add registration completion if applicable
            if is_complete and not user.get('registration_complete', False):
                update_expression += ", registration_complete = :complete, registration_completed_at = :completed_at"
                expression_values[':complete'] = True
                expression_values[':completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Perform atomic update
            response = self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            updated_user = response['Attributes']
            
            logger.info("Voice embedding added successfully", extra={
                "user_id": user_id,
                "total_embeddings": len(current_embeddings),
                "registration_complete": is_complete,
                "embedding_dimensions": len(embedding)
            })
            
            return {
                'user_id': user_id,
                'total_embeddings': new_embedding_count,
                'registration_complete': is_complete,
                'updated_user': updated_user
            }
            
        except ClientError as e:
            aws_config_manager.handle_aws_error(e, "add_voice_embedding", user_id)
            raise
        except Exception as e:
            logger.error("Failed to add voice embedding", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    async def get_user_embeddings(self, user_id: str) -> List[VoiceEmbedding]:
        """
        Get all voice embeddings for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of user's voice embeddings
        """
        try:
            user = await self.get_user(user_id)
            if not user:
                return []
            
            embeddings_data = user.get('voice_embeddings', [])
            voice_embeddings = []
            
            for embedding_data in embeddings_data:
                try:
                    # Extract metadata
                    audio_metadata = embedding_data.get('audio_metadata', {})
                    processor_info = {
                        'processor_type': audio_metadata.get('processor_type', 'unknown'),
                        'processed_at': audio_metadata.get('processed_at', '')
                    }
                    
                    # Create VoiceEmbedding domain object
                    voice_embedding = VoiceEmbedding.create(
                        embedding=embedding_data['embedding'],
                        quality_score=audio_metadata.get('quality_score', 0.0),
                        user_id=user_id,
                        sample_metadata=audio_metadata,
                        processor_info=processor_info
                    )
                    
                    voice_embeddings.append(voice_embedding)
                    
                except Exception as e:
                    logger.warning("Failed to parse voice embedding", extra={
                        "user_id": user_id,
                        "error": str(e)
                    })
                    continue
            
            logger.debug("Retrieved user embeddings", extra={
                "user_id": user_id,
                "embedding_count": len(voice_embeddings)
            })
            
            return voice_embeddings
            
        except Exception as e:
            logger.error("Failed to get user embeddings", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    async def update_user_status(
        self,
        user_id: str,
        status_update: Dict[str, Any]
    ) -> bool:
        """
        Update user registration status.
        
        Args:
            user_id: User identifier
            status_update: Status fields to update
            
        Returns:
            True if update was successful
        """
        try:
            if not status_update:
                raise ValueError("No status updates provided")
            
            # Build update expression
            update_parts = []
            expression_values = {}
            
            for field, value in status_update.items():
                update_parts.append(f"{field} = :{field}")
                expression_values[f":{field}"] = value
            
            # Always update the updated_at timestamp
            update_parts.append("updated_at = :updated_at")
            expression_values[":updated_at"] = datetime.now(timezone.utc).isoformat()
            
            update_expression = "SET " + ", ".join(update_parts)
            
            response = self.table.update_item(
                Key={'user_id': user_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues='ALL_NEW'
            )
            
            logger.info("User status updated successfully", extra={
                "user_id": user_id,
                "updated_fields": list(status_update.keys())
            })
            
            return True
            
        except ClientError as e:
            aws_config_manager.handle_aws_error(e, "update_user_status", user_id)
            return False
        except Exception as e:
            logger.error("Failed to update user status", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return False
    
    async def get_user_registration_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get user registration completion status.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with registration status information
        """
        try:
            user = await self.get_user(user_id)
            if not user:
                return {
                    'user_exists': False,
                    'embedding_count': 0,
                    'registration_complete': False,
                    'required_samples': self.required_samples
                }
            
            embeddings = user.get('voice_embeddings', [])
            
            status = {
                'user_exists': True,
                'user_id': user_id,
                'embedding_count': len(embeddings),
                'required_samples': self.required_samples,
                'registration_complete': user.get('registration_complete', False),
                'samples_remaining': max(0, self.required_samples - len(embeddings)),
                'last_embedding_date': None,
                'registration_completed_at': user.get('registration_completed_at')
            }
            
            # Get last embedding date
            if embeddings:
                last_embedding = max(embeddings, key=lambda x: x.get('created_at', ''))
                status['last_embedding_date'] = last_embedding.get('created_at')
            
            logger.debug("Generated user registration status", extra=status)
            return status
            
        except Exception as e:
            logger.error("Failed to get user registration status", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    async def get_user_embedding_count(self, user_id: str) -> int:
        """
        Get count of voice embeddings for a user (async).
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of voice embeddings stored
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id},
                ProjectionExpression='voice_embeddings_count, voice_embeddings'  # Get both for fallback
            )
            
            if 'Item' not in response:
                raise ValueError(f"User {user_id} not found")
            
            user = response['Item']
            
            # Use persisted count if available, fallback to calculated count
            embedding_count = user.get('voice_embeddings_count')
            if embedding_count is None:
                # Fallback for existing users without voice_embeddings_count field
                embedding_count = len(user.get('voice_embeddings', []))
                logger.warning("Using fallback embedding count calculation", extra={
                    "user_id": user_id,
                    "embedding_count": embedding_count
                })
            
            logger.debug("Retrieved user embedding count", extra={
                "user_id": user_id,
                "embedding_count": embedding_count,
                "source": "persisted" if user.get('voice_embeddings_count') is not None else "calculated"
            })
            
            return embedding_count
            
        except Exception as e:
            logger.error("Failed to get user embedding count", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    def is_registration_complete(self, user_id: str) -> bool:
        """
        Check if user registration is complete.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if user has completed voice registration
        """
        try:
            response = self.table.get_item(Key={'user_id': user_id})
            
            if 'Item' not in response:
                return False
            
            user = response['Item']
            
            # Check both embedding count and explicit flag
            embedding_count = len(user.get('voice_embeddings', []))
            explicit_complete = user.get('registration_complete', False)
            
            is_complete = embedding_count >= self.required_samples or explicit_complete
            
            logger.debug("Checked registration completion", extra={
                "user_id": user_id,
                "embedding_count": embedding_count,
                "required_samples": self.required_samples,
                "explicit_complete": explicit_complete,
                "is_complete": is_complete
            })
            
            return is_complete
            
        except Exception as e:
            logger.error("Failed to check registration completion", extra={
                "user_id": user_id,
                "error": str(e)
            })
            return False
