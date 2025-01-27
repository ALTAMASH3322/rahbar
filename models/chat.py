from . import db

class Chat(db.Model):
    __tablename__ = 'chats'
    chat_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('Sent', 'Delivered', 'Read'), default='Sent')
    sent_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], back_populates='chats_sent')
    receiver = db.relationship('User', foreign_keys=[receiver_id], back_populates='chats_received')