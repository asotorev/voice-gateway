"""
DynamoDB implementation of UserRepositoryPort.
Provides real persistence using single table design with voice embeddings.
"""
from typing import Optional
from datetime import datetime
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
        Get user by ID using primary key.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            Optional[User]: User if found, None otherwise
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
            'updated_at': datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        # Add voice embeddings if they exist
        if hasattr(user, 'voice_embeddings') and user.voice_embeddings:
            item['voice_embeddings'] = self._convert_floats_to_decimal(user.voice_embeddings)
        
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
        
        return user