from . import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    sex = db.Column(db.Enum('M', 'F'), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)
    status = db.Column(db.Enum('Active', 'Inactive'), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    role = db.relationship('Role', back_populates='users')

    # Relationships for GrantorGrantee
    grantor_grantees = db.relationship(
        'GrantorGrantee',
        foreign_keys='GrantorGrantee.grantor_id',
        back_populates='grantor'
    )
    grantee_grantees = db.relationship(
        'GrantorGrantee',
        foreign_keys='GrantorGrantee.grantee_id',
        back_populates='grantee'
    )

    # Other relationships
    payments = db.relationship('Payment', back_populates='user')
    approvals = db.relationship('Approval', back_populates='approver')
    notifications = db.relationship('Notification', back_populates='user')
    grantee_details = db.relationship('GranteeDetails', back_populates='user', uselist=False)
    bank_details = db.relationship('BankDetails', back_populates='user', uselist=False)
    chats_sent = db.relationship('Chat', foreign_keys='Chat.sender_id', back_populates='sender')
    chats_received = db.relationship('Chat', foreign_keys='Chat.receiver_id', back_populates='receiver')