import os
from typing import Any
from dotenv import load_dotenv

load_dotenv() 
    
PLACES_API_FIELDS = [
    "id", "displayName", "formattedAddress", "location",
    "primaryType", "types", "priceLevel", "rating", "userRatingCount",
    "regularOpeningHours", "reviews"
]
