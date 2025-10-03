from datetime import datetime
import json
import uuid


class UUIDEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles UUID and datetime objects.
    
    This encoder extends the standard JSONEncoder to properly serialize:
    - UUID objects (converted to strings)
    - datetime objects (converted to ISO format)
    """
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # Convert UUID to string
            return str(obj)
        elif isinstance(obj, datetime):
            # Convert datetime to ISO format string
            return obj.isoformat()
        # Let the base class handle other types or raise TypeError
        return super().default(obj)