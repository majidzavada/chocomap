from app.extensions import db

class MapConfig(db.Model):
    __tablename__ = 'map_config'

    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.Text, nullable=False)
    environment = db.Column(db.String(10), nullable=False)
    last_validated = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.now())