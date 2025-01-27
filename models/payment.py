from . import db

class Payment(db.Model):
    __tablename__ = 'payments'
    payment_id = db.Column(db.Integer, primary_key=True)
    grantor_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    grantee_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    receipt_url = db.Column(db.String(255))
    status = db.Column(db.Enum('Pending', 'Received', 'Paid', 'Completed'), default='Pending')
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='payments')
    approvals = db.relationship('Approval', back_populates='payment')