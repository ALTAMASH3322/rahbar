from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from .user import User
from .role import Role
from .permission import Permission
from .role_permission import RolePermission
from .institution import Institution
from .course import Course
from .grantor_grantee import GrantorGrantee
from .payment import Payment
from .approval import Approval
from .notification import Notification
from .grantee_details import GranteeDetails
from .chat import Chat
from .bank_details import BankDetails
from .rcc_center import RCCCenter
from .installment_details import InstallmentDetails

# Define relationships here (if not already defined in individual model files)