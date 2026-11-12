# Import all models so SQLAlchemy registers them with Base.metadata
from app.models.zone import Zone, ZoneEdge  # noqa
from app.models.incident import Incident  # noqa
from app.models.resource import Resource, Deployment  # noqa
