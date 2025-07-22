"""
Advanced logging decorators infrastructure for Voice Gateway.
Provides structured, context-rich, and secure logging for infrastructure operations.
"""
import logging
import functools
import time
import uuid
import inspect
from typing import Dict, Any, Optional, Callable, Set
from datetime import datetime, timezone

from app.infrastructure.config.infrastructure_settings import infra_settings
from .log_config import get_logger


# Default sensitive fields blacklist
DEFAULT_SENSITIVE_FIELDS: Set[str] = {
    'password', 'password_hash', 'secret', 'token', 'key', 'api_key',
    'voice_samples', 'audio_data', 'embeddings', 'voice_embedding',
    'embedding_vector', 'biometric_data', 'private_key', 'auth_token'
}


def op_config(
    level: str = "INFO",
    args: bool = True,
    result: bool = True,
    perform: bool = True,
    blacklist: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Create operation config with flexible overrides for logging decorators.
    
    Args:
        level: Logging level (default INFO)
        args: Whether to log function arguments
        result: Whether to log operation result
        perform: Whether to log timing metrics
        blacklist: Additional sensitive fields to mask
        
    Returns:
        dict: Configuration for the decorator
    """
    return {
        "level": level,
        "include_args": args,
        "include_result": result,
        "include_performance": perform,
        "sensitive_fields": blacklist or set()
    }


def _sanitize_sensitive_data(data: Any, blacklist: Set[str]) -> Any:
    """
    Recursively sanitize sensitive data from logs.
    Replaces values of keys matching sensitive fields with [REDACTED].
    
    Args:
        data: Data to sanitize (dict, list, etc.)
        blacklist: Set of sensitive field names
        
    Returns:
        Sanitized data with sensitive fields masked
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in str(key).lower() for sensitive in blacklist):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = _sanitize_sensitive_data(value, blacklist)
        return sanitized
    elif isinstance(data, (list, tuple)):
        return [_sanitize_sensitive_data(item, blacklist) for item in data]
    elif isinstance(data, bytes):
        return f"[BINARY_DATA_{len(data)}_BYTES]"
    else:
        return data


def _build_operation_context(
    operation: str, 
    method_name: str, 
    component_name: str
) -> Dict[str, Any]:
    """
    Build base context for operation logging.
    Includes operation, component, method, timestamp, environment, and trace IDs.
    
    Args:
        operation: Operation name
        method_name: Name of the method/function
        component_name: Name of the component/class
        
    Returns:
        dict: Context for logging
    """
    return {
        "component": component_name,
        "operation": operation,
        "method": method_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": infra_settings.environment,
        "service": infra_settings.service_name,
        "aws_region": infra_settings.aws_region,
        "trace_id": f"trace_{uuid.uuid4().hex[:12]}",
        "operation_id": f"op_{uuid.uuid4().hex[:8]}"
    }


def log_infrastructure_operation(
    operation: str,
    level: str = "INFO",
    include_args: bool = False,
    include_result: bool = True,
    include_performance: bool = True,
    sensitive_fields: Optional[Set[str]] = None
) -> Callable:
    """
    Advanced decorator for infrastructure operations.
    Provides structured, context-rich, and secure logging for method execution.
    
    Args:
        operation: Business operation name
        level: Logging level 
        include_args: Whether to log function arguments
        include_result: Whether to log operation result
        include_performance: Whether to log timing metrics
        sensitive_fields: Additional sensitive fields to blacklist
        
    Returns:
        Decorated function with automatic structured logging
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get logger for this component
            component_name = f"{func.__module__}.{self.__class__.__name__}"
            logger = get_logger(component_name)
            
            # Prepare blacklist
            blacklist = DEFAULT_SENSITIVE_FIELDS.copy()
            if sensitive_fields:
                blacklist.update(sensitive_fields)
            
            # Build base context
            context = _build_operation_context(operation, func.__name__, component_name)
            
            # Add arguments if requested
            if include_args:
                sig = inspect.signature(func)
                bound_args = sig.bind(self, *args, **kwargs)
                bound_args.apply_defaults()
                
                args_dict = {k: v for k, v in bound_args.arguments.items() if k != 'self'}
                context["arguments"] = _sanitize_sensitive_data(args_dict, blacklist)
            
            # Log operation start
            start_time = time.time()
            log_level = getattr(logging, level.upper(), logging.INFO)
            
            if include_performance:
                context["status"] = "started"
            
            logger.log(log_level, f"Starting {operation}", extra={"extra_fields": context})
            
            try:
                # Execute operation
                result = func(self, *args, **kwargs)
                
                # Calculate performance
                duration_ms = (time.time() - start_time) * 1000
                
                # Build success context
                success_context = context.copy()
                success_context["status"] = "completed"
                
                if include_performance:
                    success_context["duration_ms"] = round(duration_ms, 2)
                    if duration_ms > 2000:
                        success_context["slow_operation"] = True
                
                if include_result and result is not None:
                    success_context["result"] = _sanitize_sensitive_data(result, blacklist)
                    success_context["result_type"] = type(result).__name__
                    
                    if hasattr(result, '__len__') and not isinstance(result, str):
                        success_context["result_size"] = len(result)
                
                logger.log(log_level, f"Completed {operation}", extra={"extra_fields": success_context})
                return result
                
            except Exception as e:
                # Calculate performance for failed operation
                duration_ms = (time.time() - start_time) * 1000
                
                # Build error context
                error_context = context.copy()
                error_context.update({
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2)
                })
                
                # Add stack trace in development
                if infra_settings.environment == "development":
                    import traceback
                    error_context["stack_trace"] = traceback.format_exc()
                
                # Log error
                error_level = logging.CRITICAL if level.upper() == "CRITICAL" else logging.ERROR
                logger.log(error_level, f"Failed {operation}", extra={"extra_fields": error_context})
                
                raise
        
        return wrapper
    return decorator