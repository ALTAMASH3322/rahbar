from . import db

class RCCCenter(db.Model):
    __tablename__ = 'rcc_centers'
    rcc_center_id = db.Column(db.Integer, primary_key=True)
    center_name = db.Column(db.String(255), nullable=False)
    incharge_name = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    location = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())