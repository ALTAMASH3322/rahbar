from . import db

class GrantorGrantee(db.Model):
    __tablename__ = 'grantor_grantees'
    grantor_grantee_id = db.Column(db.Integer, primary_key=True)
    grantor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    grantee_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    status = db.Column(db.Enum('Pending', 'Accepted', 'Declined'), default='Pending')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    grantor = db.relationship('User', foreign_keys=[grantor_id], back_populates='grantor_grantees')
    grantee = db.relationship('User', foreign_keys=[grantee_id], back_populates='grantee_grantees')