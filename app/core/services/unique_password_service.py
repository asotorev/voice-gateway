"""
Unique password service for Voice Gateway.
Handles password uniqueness validation using domain logic.
"""
from app.core.ports.password_service import PasswordServicePort
from app.core.ports.user_repository import UserRepositoryPort


class UniquePasswordService:
    """
    Domain service for generating unique passwords.
    
    Handles the business logic of ensuring password uniqueness
    by coordinating between password generation and repository validation.
    """
    
    def __init__(
        self, 
        password_service: PasswordServicePort,
        user_repository: UserRepositoryPort
    ):
        """
        Initialize unique password service.
        
        Args:
            password_service: Service for generating passwords
            user_repository: Repository for checking password uniqueness
        """
        self.password_service = password_service
        self.user_repository = user_repository
    
    async def generate_unique_password(self, max_attempts: int = 10) -> str:
        """
        Generate a unique password that doesn't exist in the system.
        
        Args:
            max_attempts: Maximum number of generation attempts
            
        Returns:
            str: Unique password string
            
        Raises:
            ValueError: If unable to generate unique password after max_attempts
            RuntimeError: If services are unavailable
        """
        if not self.password_service:
            raise RuntimeError("Password service not available")
        
        if not self.user_repository:
            raise RuntimeError("User repository not available")
        
        for attempt in range(max_attempts):
            # Generate a new password
            password = self.password_service.generate_password()
            
            # Hash the password for uniqueness check
            password_hash = self.password_service.hash_password(password)
            
            # Check if hash already exists
            exists = await self.user_repository.check_password_hash_exists(password_hash)
            if not exists:
                return password
        
        # Calculate total possible combinations for error message
        word_count = len(self.password_service._words) if hasattr(self.password_service, '_words') else 0
        total_combinations = word_count * (word_count - 1) if word_count > 1 else 0
        
        raise ValueError(
            f"Unable to generate unique password after {max_attempts} attempts. "
            f"Total combinations: {total_combinations}, "
            f"Consider increasing dictionary size or max_attempts."
        ) 