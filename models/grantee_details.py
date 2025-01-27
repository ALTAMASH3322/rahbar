from . import db

class GranteeDetails(db.Model):
    __tablename__ = 'grantee_details'
    grantee_detail_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    father_name = db.Column(db.String(255))
    mother_name = db.Column(db.String(255))
    father_profession = db.Column(db.String(255))
    mother_profession = db.Column(db.String(255))
    address = db.Column(db.Text)
    average_annual_salary = db.Column(db.Numeric(10, 2))
    rahbar_alumnus = db.Column(db.Enum('Y', 'N'), default='N')
    rcc_name = db.Column(db.String(255))
    course_applied = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    user = db.relationship('User', back_populates='grantee_details')