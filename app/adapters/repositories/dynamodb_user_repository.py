"""
DynamoDB implementation of UserRepositoryPort.
Provides real persistence using single table design with voice embeddings.
"""
from typing import Optional
from datetime import datetime, UTC
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from app.core.models.user import User
from app.core.ports.user_repository import UserRepositoryPort
from app.infrastructure.config.aws_config import aws_config
from app.infrastructure.config.infrastructure_settings import infra_settings
from decimal import Decimal


class DynamoDBUserRepository(UserRepositoryPort):
    """
    DynamoDB implementation of UserRepositoryPort.
    
    Uses single table design with embedded voice embeddings and relative audio paths.
    Includes GSI optimization for password hash uniqueness checks.
    """
    
    def __init__(self):
        self.table_name = infra_settings.users_table_name
        self.table = aws_config.get_table(self.table_name)
    
    async def save(self, user: User) -> User:
        """
        Save user to DynamoDB.
        
        Args:
            user: User domain entity to save
            
        Returns:
            User: Saved user with any updates
            
        Raises:
            Exception: If save operation fails
        """
        # Check for duplicate email before saving
        existing_user = await self.get_by_email(user.email)
        if existing_user and str(existing_user.id) != str(user.id):
            raise ValueError(f"User with email {user.email} already exists")
        try:
            item = self._to_dynamodb_item(user)
            
            # Use put_item for upsert behavior
            self.table.put_item(Item=item)
            
            return user
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConditionalCheckFailedException':
                raise ValueError(f"User with email {user.email} already exists")
            else:
                raise Exception(f"Failed to save user: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error saving user: {str(e)}")
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email using GSI.
        
        Args:
            email: User email to search for
            
        Returns:
            Optional[User]: User if found, None otherwise
        """
        try:
            response = self.table.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            items = response.get('Items', [])
            if not items:
                return None
                
            # Should only be one user per email
            item = items[0]
            return self._from_dynamodb_item(item)
            
        except ClientError as e:
            raise Exception(f"Failed to get user by email: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting user by email: {str(e)}")
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user by ID using primary key (returns complete user data).
        
        Args:
            user_id: User ID to search for
            
        Returns:
            Optional[User]: Complete user if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id}
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            return self._from_dynamodb_item(item)
            
        except ClientError as e:
            raise Exception(f"Failed to get user by ID: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting user by ID: {str(e)}")

    async def get_profile_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user data optimized for profile display.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            Optional[User]: User with profile fields if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id},
                ProjectionExpression='user_id, name, email, created_at, voice_setup_complete'
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            return self._from_dynamodb_item(item)
            
        except ClientError as e:
            raise Exception(f"Failed to get user profile: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting user profile: {str(e)}")

    async def get_auth_status_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user data optimized for authentication status.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            Optional[User]: User with auth status fields if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id},
                ProjectionExpression='user_id, voice_setup_complete, voice_embeddings_count',
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            return self._from_dynamodb_item(item)
            
        except ClientError as e:
            raise Exception(f"Failed to get user auth status: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting user auth status: {str(e)}")

    async def get_registration_status_by_id(self, user_id: str) -> Optional[User]:
        """
        Get user data optimized for registration status.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            Optional[User]: User with registration status fields if found, None otherwise
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id},
                ProjectionExpression='user_id, voice_embeddings_count, updated_at',
            )
            
            item = response.get('Item')
            if not item:
                return None
                
            return self._from_dynamodb_item(item)
            
        except ClientError as e:
            raise Exception(f"Failed to get user registration status: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting user registration status: {str(e)}")
    
    async def check_password_hash_exists(self, password_hash: str) -> bool:
        """
        Check if a password hash exists.
        
        Args:
            password_hash: Hash to check for existence
            
        Returns:
            bool: True if hash exists, False otherwise
            
        Raises:
            Exception: If query fails
        """
        try:
            # Use GSI for immediate lookup
            response = self.table.query(
                IndexName='password-hash-index',
                KeyConditionExpression='password_hash = :hash',
                ExpressionAttributeValues={':hash': password_hash},
                Select='COUNT'  # Only get count, not actual items
            )
            
            # If count > 0, hash exists
            return response.get('Count', 0) > 0
            
        except ClientError as e:
            raise Exception(f"Failed to check password hash: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error checking password hash: {str(e)}")
    
    async def get_user_embedding_count(self, user_id: str) -> int:
        """
        Get count of voice embeddings for a user (optimized query).
        
        Args:
            user_id: User ID to get embedding count for
            
        Returns:
            Number of voice embeddings stored
            
        Raises:
            Exception: If user not found or query fails
        """
        try:
            response = self.table.get_item(
                Key={'user_id': user_id},
                ProjectionExpression='voice_embeddings_count, voice_embeddings'  # Get both for fallback
            )
            
            item = response.get('Item')
            if not item:
                raise Exception(f"User {user_id} not found")
            
            # Use persisted count if available, fallback to calculated count
            embedding_count = item.get('voice_embeddings_count')
            if embedding_count is None:
                # Fallback for existing users without voice_embeddings_count field
                embedding_count = len(item.get('voice_embeddings', []))
            
            return int(embedding_count)
            
        except ClientError as e:
            raise Exception(f"Failed to get embedding count: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error getting embedding count: {str(e)}")

    async def delete(self, user_id: str) -> None:
        """Delete a user by ID from DynamoDB."""
        try:
            self.table.delete_item(Key={'user_id': user_id})
        except ClientError as e:
            raise Exception(f"Failed to delete user: {e.response['Error']['Message']}")
        except Exception as e:
            raise Exception(f"Unexpected error deleting user: {str(e)}")
    
    def _to_dynamodb_item(self, user: User) -> dict:
        """
        Convert User domain entity to DynamoDB item.
        
        Args:
            user: User domain entity
            
        Returns:
            dict: DynamoDB item representation
        """
        item = {
            'user_id': str(user.id),
            'name': user.name,
            'email': user.email,
            'password_hash': user.password_hash,
            'created_at': user.created_at.isoformat(),
            'updated_at': datetime.now(UTC).isoformat(),
            'is_active': True
        }
        
        # Add voice embeddings if they exist
        if hasattr(user, 'voice_embeddings') and user.voice_embeddings:
            item['voice_embeddings'] = self._convert_floats_to_decimal(user.voice_embeddings)
        
        # Add calculated fields if they exist (as dynamic attributes)
        if hasattr(user, 'voice_embeddings_count'):
            item['voice_embeddings_count'] = user.voice_embeddings_count
        
        return item
    
    def _convert_floats_to_decimal(self, obj):
        """
        Convert all float values in a structure (including nested lists and dicts)
        to Decimal for DynamoDB compatibility.
        This ensures that any float, even if deeply nested, is stored as Decimal,
        which is required by boto3/DynamoDB and avoids type errors when saving items.
        """
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, list):
            return [self._convert_floats_to_decimal(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: self._convert_floats_to_decimal(v) for k, v in obj.items()}
        else:
            return obj
    
    def _from_dynamodb_item(self, item: dict) -> User:
        """
        Convert DynamoDB item to User domain entity.
        
        Args:
            item: DynamoDB item
            
        Returns:
            User: User domain entity
        """
        user = User(
            id=item['user_id'],
            name=item['name'],
            email=item['email'],
            password_hash=item['password_hash'],
            created_at=datetime.fromisoformat(item['created_at'])
        )
        
        # Add voice embeddings if they exist
        if 'voice_embeddings' in item:
            user.voice_embeddings = item['voice_embeddings']
        
        # Add calculated fields as dynamic attributes
        if 'voice_embeddings_count' in item:
            user.voice_embeddings_count = item['voice_embeddings_count']
        
        return user