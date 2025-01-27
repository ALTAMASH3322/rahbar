from . import db

class Course(db.Model):
    __tablename__ = 'courses'
    course_id = db.Column(db.Integer, primary_key=True)
    institution_id = db.Column(db.Integer, db.ForeignKey('institutions.institution_id'), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    course_description = db.Column(db.Text)
    fees_per_semester = db.Column(db.Numeric(10, 2), nullable=False)
    duration_in_months = db.Column(db.Integer, nullable=False)
    number_of_semesters = db.Column(db.Integer, nullable=False)
    even_semester_due_date = db.Column(db.Date)
    odd_semester_due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    institution = db.relationship('Institution', back_populates='courses')