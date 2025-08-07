"""
DynamoDB operations for Lambda audio processing.

This module provides DynamoDB-specific operations for managing user records,
updating voice embeddings, and tracking registration completion status
in the Lambda processing pipeline.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from ..utils.aws_lambda_config import aws_lambda_config_manager

logger = logging.getLogger(__name__)


class DynamoDBUserOperations:
    """
    DynamoDB operations for user voice embedding management.
    
    Handles user record updates, voice embedding storage, and registration
    completion tracking with proper error handling and atomic operations.
    """
    
    def __init__(self):
        """Initialize DynamoDB user operations."""
        self.dynamodb_resource = aws_lambda_config_manager.dynamodb_resource
        self.table_name = aws_lambda_config_manager.get_users_table_name()
        self.table = self.dynamodb_resource.Table(self.table_name)
        self.required_samples = int(os.getenv('REQUIRED_AUDIO_SAMPLES', '3'))
        
        logger.info("DynamoDB user operations initialized", extra={
            "table": self.table_name,
            "required_samples": self.required_samples
        })
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user record from DynamoDB.
        
        Args:
            user_id: User identifier
            
        Returns:
            User record dict or None if not found
            
        Raises:
            ClientError: If DynamoDB operation fails
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
            aws_lambda_config_manager.handle_aws_error(e, "get_user", user_id)
            raise
        except Exception as e:
            logger.error("Failed to get user", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    def add_voice_embedding(self, user_id: str, embedding: List[float], audio_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a voice embedding to user's record.
        
        Args:
            user_id: User identifier
            embedding: Voice embedding vector
            audio_metadata: Metadata about the processed audio file
            
        Returns:
            Updated user record with embedding count and completion status
            
        Raises:
            ValueError: If user not found or embedding is invalid
            ClientError: If DynamoDB operation fails
        """
        logger.info("Adding voice embedding to user", extra={
            "user_id": user_id,
            "embedding_dimensions": len(embedding),
            "audio_file": audio_metadata.get('file_name', 'unknown')
        })
        
        try:
            # Validate embedding
            if not embedding or not isinstance(embedding, list):
                raise ValueError("Invalid embedding: must be non-empty list")
            
            if not all(isinstance(x, (int, float)) for x in embedding):
                raise ValueError("Invalid embedding: all values must be numeric")
            
            # Get current user record
            user = self.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Prepare embedding entry
            embedding_entry = {
                'embedding': embedding,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'audio_metadata': {
                    'file_name': audio_metadata.get('file_name', ''),
                    'file_size': audio_metadata.get('size_bytes', 0),
                    'processed_at': datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Get current embeddings or initialize empty list
            current_embeddings = user.get('voice_embeddings', [])
            
            # Add new embedding
            current_embeddings.append(embedding_entry)
            
            # Check if registration is complete
            is_complete = len(current_embeddings) >= self.required_samples
            
            # Update user record atomically
            update_expression = "SET voice_embeddings = :embeddings, updated_at = :updated_at"
            expression_values = {
                ':embeddings': current_embeddings,
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
                'total_embeddings': len(current_embeddings),
                'registration_complete': is_complete,
                'updated_user': updated_user
            }
            
        except ClientError as e:
            aws_lambda_config_manager.handle_aws_error(e, "add_voice_embedding", user_id)
            raise
        except Exception as e:
            logger.error("Failed to add voice embedding", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    def get_user_embedding_count(self, user_id: str) -> int:
        """
        Get count of voice embeddings for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of voice embeddings stored
            
        Raises:
            ValueError: If user not found
        """
        try:
            user = self.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            embedding_count = len(user.get('voice_embeddings', []))
            
            logger.debug("Retrieved user embedding count", extra={
                "user_id": user_id,
                "embedding_count": embedding_count
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
            user = self.get_user(user_id)
            if not user:
                return False
            
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
    
    def update_user_status(self, user_id: str, status_updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user status fields.
        
        Args:
            user_id: User identifier
            status_updates: Dict of fields to update
            
        Returns:
            Updated user record
            
        Raises:
            ValueError: If user not found
            ClientError: If DynamoDB operation fails
        """
        try:
            if not status_updates:
                raise ValueError("No status updates provided")
            
            # Build update expression
            update_parts = []
            expression_values = {}
            
            for field, value in status_updates.items():
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
            
            updated_user = response['Attributes']
            
            logger.info("User status updated successfully", extra={
                "user_id": user_id,
                "updated_fields": list(status_updates.keys())
            })
            
            return updated_user
            
        except ClientError as e:
            aws_lambda_config_manager.handle_aws_error(e, "update_user_status", user_id)
            raise
        except Exception as e:
            logger.error("Failed to update user status", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise
    
    def get_user_voice_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get summary of user's voice registration status.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with voice registration summary
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return {
                    'user_exists': False,
                    'embedding_count': 0,
                    'registration_complete': False,
                    'required_samples': self.required_samples
                }
            
            embeddings = user.get('voice_embeddings', [])
            
            summary = {
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
                summary['last_embedding_date'] = last_embedding.get('created_at')
            
            logger.debug("Generated user voice summary", extra=summary)
            return summary
            
        except Exception as e:
            logger.error("Failed to get user voice summary", extra={
                "user_id": user_id,
                "error": str(e)
            })
            raise


# Global DynamoDB operations instance for Lambda function
dynamodb_operations = DynamoDBUserOperations()
