"""AgriDirect produce listings management module.

Implements Module 2 (Catalog, Listings, and Media Assets) of AgriDirect:
- Produce categories taxonomy (ProduceCategory)
- Farmer produce listings management (ProduceListing)
- Listing images management (ListingImage)
"""

from app.listings.routes import router

__all__ = ["router"]

