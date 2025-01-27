from . import db

class InstallmentDetails(db.Model):
    __tablename__ = 'installment_details'
    installment_id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    installment_type = db.Column(db.Enum('Monthly', 'Quarterly', 'Half-Yearly', 'Yearly'), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())