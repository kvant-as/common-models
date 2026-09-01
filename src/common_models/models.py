import secrets
import string
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from .timeutils import current_utc_time
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Numeric, UniqueConstraint

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)

    type = db.Column(db.String(13), default='Респондент')
    is_admin = db.Column(db.Boolean, default=False, server_default='false')
    is_auditor = db.Column(db.Boolean, default=False, server_default='false')
    is_approver = db.Column(db.Boolean, default=False, server_default='false')
    is_reader = db.Column(db.Boolean, default=False, server_default='false')
    
    email = db.Column(db.String(), unique=True)
    fio = db.Column(db.String(100))
    last_name = db.Column(db.String())
    first_name = db.Column(db.String())
    patronymic_name = db.Column(db.String())
    
    telephone = db.Column(db.String())
    post = db.Column(db.String())
    
    password = db.Column(db.String())
    begin_time = db.Column(db.DateTime, default=current_utc_time)  # дата создания аккаунта
    # последняя активность теперь хранится по приложениям в UserAppActivity.last_active
    reset_password_token = db.Column(db.String(255), nullable=True)
    reset_password_expires = db.Column(db.DateTime, nullable=True)
    
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    reports = db.relationship('Report', backref='user', lazy=True, cascade="all, delete-orphan")
    organization = db.relationship('Organization', back_populates='users')
    plans = db.relationship('Plan', back_populates='user', lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship('PlanTicket', back_populates='user', lazy=True)
    notifications = db.relationship('Notification', back_populates='user', lazy=True, cascade="all, delete-orphan")
    created_chats = db.relationship('Chat', back_populates='created_by', cascade='all, delete-orphan')
    
    activity = db.relationship('UserAppActivity', back_populates='user',
                               lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'


class UserAppActivity(db.Model):
    """Первое появление и последняя активность пользователя в каждом приложении.

    Одна строка на пару (user, app). Обновляется через
    ``common_models.touch_user_activity`` из каждого приложения.
    """
    __tablename__ = 'user_app_activity'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'app', name='uq_user_app_activity'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    app = db.Column(db.String(32), nullable=False)  # 'enplans' | 'erespondentn'
    first_seen = db.Column(db.DateTime, nullable=False, default=current_utc_time)
    last_active = db.Column(db.DateTime, nullable=False, default=current_utc_time)

    user = db.relationship('User', back_populates='activity')

    def __repr__(self):
        return f'<UserAppActivity user={self.user_id} app={self.app} last_active={self.last_active}>'


class Organization(db.Model):
    __tablename__ = 'organization'
    id = db.Column(db.Integer, primary_key=True)
    
    is_active = db.Column(db.Boolean, default=True)
    full_name = db.Column(db.String())
    okpo = db.Column(db.String, unique=True)
    ynp = db.Column(db.String(), nullable=True)

    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'))
    ministry_id = db.Column(db.Integer, db.ForeignKey('ministry.id'), nullable=True)
    
    is_regular = db.Column(db.Boolean, default=False, server_default='false')
    is_coordinator = db.Column(db.Boolean, default=False, server_default='false')
    is_approver = db.Column(db.Boolean, default=False, server_default='false')
    is_region_management = db.Column(db.Boolean, default=False, server_default='false')
    
    region = db.relationship("Region", back_populates="organizations")
    ministry = db.relationship("Ministry", back_populates="organizations")
    users = db.relationship("User", back_populates="organization")
    reports = db.relationship('Report', backref='organization', lazy=True)
    
    approval_paths = db.relationship("PlanApprovalPath", foreign_keys="PlanApprovalPath.organization_id", back_populates="organization")
    plans = db.relationship("Plan", foreign_keys="Plan.org_id", back_populates="organization")

    
class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(), nullable=False)
    organizations = db.relationship("Organization", back_populates="region")
    
class Ministry(db.Model):
    __tablename__ = 'ministry'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    organizations = db.relationship('Organization', back_populates="ministry")

class News(db.Model):
    __tablename__ = 'news'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    text = db.Column(db.String(4000))
    img_name = db.Column(db.String(255))
    
    is_erespondentn = db.Column(db.Boolean, default=False)
    is_enplans = db.Column(db.Boolean, default=False)
    
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    views_count = db.Column(db.Integer, default=0)
    
    created_time = db.Column(db.DateTime, nullable=False, default=current_utc_time)

# ====================== ERESPONDENTN

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    create_time = db.Column(db.DateTime, default=current_utc_time)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    to_admin = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    read_time = db.Column(db.DateTime, nullable=True)
    text = db.Column(db.String(500))
    sender = db.relationship('User', foreign_keys=[sender_id], backref=backref('sent_messages', lazy=True, cascade="all, delete-orphan"))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=backref('received_messages', lazy=True, cascade="all, delete-orphan"))

class Report(db.Model):
    __tablename__ = 'report'
    id = db.Column(db.Integer, primary_key=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))  
    year = db.Column(db.Integer)
    quarter = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  
    versions = db.relationship('Version_report', backref='report', cascade="all, delete-orphan")

class Version_report(db.Model):
    __tablename__ = 'version_report'
    id = db.Column(db.Integer, primary_key=True)
    begin_time = db.Column(db.DateTime, default=current_utc_time)
    change_time = db.Column(db.DateTime)
    sent_time = db.Column(db.DateTime)
    audit_time = db.Column(db.DateTime)
    status = db.Column(db.String(20))
    hasNot = db.Column(db.Boolean, default=False)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'))
    sections = db.relationship('Sections', backref='version_report', lazy=True, cascade="all, delete-orphan")
    tickets = db.relationship('Ticket', back_populates='version_report', lazy=True, cascade="all, delete-orphan")

class Ticket(db.Model):
    __tablename__ = 'ticket'
    id = db.Column(db.Integer, primary_key=True)
    begin_time = db.Column(db.DateTime, default=current_utc_time)
    luck = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(500))
    version_report_id = db.Column(db.Integer, db.ForeignKey('version_report.id'))
    version_report = db.relationship("Version_report", back_populates="tickets")

class DirUnit(db.Model):
    __tablename__ = 'DirUnit'
    IdUnit = db.Column(db.Integer, primary_key=True)
    CodeUnit = db.Column(db.String(400))
    NameUnit = db.Column(db.String(400))

    def __repr__(self):
        return str(self.CodeUnit)

class DirProduct(db.Model):
    __tablename__ = 'DirProduct'
    id = db.Column(db.Integer, primary_key=True)
    CodeProduct = db.Column(db.String(400))
    NameProduct = db.Column(db.String(400))
    IsFuel = db.Column(db.Boolean)
    IsHeat = db.Column(db.Boolean) 
    IsElectro = db.Column(db.Boolean)
    IdUnit = db.Column(db.Integer, db.ForeignKey('DirUnit.IdUnit'))
    DateStart = db.Column(db.DateTime)
    DateEnd = db.Column(db.DateTime)
    unit = relationship("DirUnit", foreign_keys=[IdUnit], backref="products")

    def __repr__(self):
        return str(self.NameProduct)

class Sections(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True) 
    id_version = db.Column(db.Integer, db.ForeignKey('version_report.id'))
    id_product = db.Column(db.Integer, db.ForeignKey('DirProduct.id'))
    code_product = db.Column(db.String)
    section_number = db.Column(db.Integer)
    Oked = db.Column(db.String(20))
    produced = db.Column(Numeric(scale=2))
    Consumed_Quota = db.Column(Numeric(scale=2))
    Consumed_Fact = db.Column(Numeric(scale=2))
    Consumed_Total_Quota = db.Column(Numeric(scale=2))
    Consumed_Total_Fact = db.Column(Numeric(scale=2))
    total_differents = db.Column(Numeric(scale=2))
    note = db.Column(db.String(200))
    product = relationship("DirProduct", foreign_keys=[id_product], backref="sections")

# ====================== ENPLANS

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    message = db.Column(db.String(140), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    user = db.relationship('User', back_populates='notifications')

def generate_static_token(length=20):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class PlanApprovalPath(db.Model):
    __tablename__ = 'plan_approval_paths'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    step_order = db.Column(db.Integer, nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    step_type = db.Column(db.String(20), nullable=False)
    is_viewed = db.Column(db.Boolean, default=False)
    viewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    
    plan = db.relationship("Plan", back_populates="approval_paths")
    organization = db.relationship("Organization", foreign_keys=[organization_id], back_populates="approval_paths")
    
    STEP_TYPES = {
        'region': 'Региональное управление',
        'coordinator': 'Согласовывающая организация',
        'approver': 'Утверждающая организация'
    }
    
    @property
    def step_type_label(self):
        return self.STEP_TYPES.get(self.step_type, self.step_type)
    
    def __repr__(self):
        return f'<PlanApprovalPath plan_id={self.plan_id} step_order={self.step_order} type={self.step_type}>'

class PlanColumnConfig(db.Model):
    __tablename__ = 'plan_column_configs'
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(50), nullable=False)
    
    plan = db.relationship("Plan", back_populates="column_configs")

class Plan(db.Model):
    __tablename__ = 'plans'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(32), unique=True, nullable=False, default=lambda: generate_static_token(), index=True)
    year = db.Column(db.Integer, nullable=False)
    begin_time = db.Column(db.DateTime, nullable=False, default=current_utc_time)
    change_time = db.Column(db.DateTime, nullable=False, default=current_utc_time)
    sent_time = db.Column(db.DateTime)
    audit_time = db.Column(db.DateTime)
    
    energy_saving = db.Column(Numeric(scale=1))
    share_fuel = db.Column(Numeric(scale=1))
    saving_fuel = db.Column(Numeric(scale=1))
    share_energy = db.Column(Numeric(scale=1))
    
    afch = db.Column(db.Boolean, default=False)
    usd_rate = db.Column(Numeric(scale=4))
    cost_per_toe_usd = db.Column(Numeric(scale=2))
    
    is_draft = db.Column(db.Boolean, default=True)
    is_control = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    
    is_error = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    
    plan_type = db.Column(db.String(50), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    tickets = db.relationship('PlanTicket', back_populates='plan', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', back_populates='plan', lazy=True, cascade="all, delete-orphan")
    indicators_usage = db.relationship('IndicatorUsage', back_populates='plan', lazy=True, cascade="all, delete-orphan")
    column_configs = db.relationship('PlanColumnConfig', back_populates='plan', lazy=True, cascade="all, delete-orphan")
    approval_paths = db.relationship('PlanApprovalPath', back_populates='plan', lazy=True, cascade="all, delete-orphan")
    
    user = db.relationship("User", back_populates="plans")
    organization = db.relationship("Organization", foreign_keys=[org_id], back_populates="plans")

class PlanTicket(db.Model):
    __tablename__ = 'Plan_tickets'
    id = db.Column(db.Integer, primary_key=True)
    begin_time = db.Column(db.DateTime)
    luck = db.Column(db.Boolean, default=False)
    is_system = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(500), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    plan = db.relationship("Plan", back_populates="tickets")
    user = db.relationship("User", back_populates="tickets")

class Unit(db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(400), unique=True, nullable=False)

class Direction(db.Model):
    __tablename__ = 'directions'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(400))
    name = db.Column(db.String(400))
    id_unit = db.Column(db.Integer, db.ForeignKey('units.id'))
    
    DateStart = db.Column(db.DateTime, default=current_utc_time)
    DateEnd = db.Column(db.DateTime)
    
    is_econom = db.Column(db.Boolean)
    is_increase = db.Column(db.Boolean)
    
    unit = db.relationship('Unit', backref='directions', foreign_keys=[id_unit])

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    id_direction = db.Column(db.Integer, db.ForeignKey('directions.id'), nullable=False)
    id_plan = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    name = db.Column(db.String(4000), nullable=False)
    display_code = db.Column(db.String(400))
    
    Volume = db.Column(db.Integer)
    EffTut = db.Column(Numeric(scale=2))
    EffRub = db.Column(db.Integer)
    ExpectedQuarter = db.Column(db.String())
    EffCurrYear = db.Column(Numeric(scale=2))
    Payback = db.Column(Numeric(scale=1))
    ObchVolumeFin = db.Column(db.Integer)
    VolumeFinCurrentYear = db.Column(db.Integer)
    BudgetState = db.Column(db.Integer)
    BudgetRep = db.Column(db.Integer)
    BudgetLoc = db.Column(db.Integer)
    BudgetOther = db.Column(db.Integer)
    MoneyOwn = db.Column(db.Integer)
    MoneyLoan = db.Column(db.Integer)
    MoneyOther = db.Column(db.Integer)
    
    is_local = db.Column(db.Boolean)
    is_corrected = db.Column(db.Boolean, default=False)
    is_econom = db.Column(db.Boolean)
    is_increase = db.Column(db.Boolean)
    
    order = db.Column(db.Integer, default=None)
    plan = db.relationship("Plan", back_populates="events")
    direction = db.relationship('Direction', backref='events', foreign_keys=[id_direction])

    def as_dict(self):
        is_double_effect = self.direction.is_econom and self.direction.is_increase if self.direction else False
        
        return {
            'id': self.id,
            'name': self.name,
            'Volume': self.Volume,
            'EffTut': float(self.EffTut) if self.EffTut else None,
            'EffRub': self.EffRub,
            'ExpectedQuarter': self.ExpectedQuarter,
            'EffCurrYear': float(self.EffCurrYear) if self.EffCurrYear else None,
            'Payback': float(self.Payback) if self.Payback else None,
            'ObchVolumeFin': self.ObchVolumeFin,
            'VolumeFinCurrentYear': self.VolumeFinCurrentYear,
            'BudgetState': self.BudgetState,
            'BudgetRep': self.BudgetRep,
            'BudgetLoc': self.BudgetLoc,
            'BudgetOther': self.BudgetOther,
            'MoneyOwn': self.MoneyOwn,
            'MoneyLoan': self.MoneyLoan,
            'MoneyOther': self.MoneyOther,
            'is_local': self.is_local,
            'is_corrected': self.is_corrected,
            'is_econom': self.is_econom,
            'is_increase': self.is_increase,
            'is_double_effect': is_double_effect,
            'direction_code': self.direction.code if self.direction else None,
            'direction_name': self.direction.name if self.direction else None
        }

class Indicator(db.Model):
    __tablename__ = 'indicators'
    id = db.Column(db.Integer, primary_key=True)
    id_unit = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    code = db.Column(db.String(400))
    name = db.Column(db.String(400))
    CoeffToTut = db.Column(Numeric(scale=3))
    
    is_local = db.Column(db.Boolean, default=False)
    is_renewable = db.Column(db.Boolean, default=False)
    
    IsMandatory = db.Column(db.Boolean)
    Group = db.Column(db.Float)
    RowN = db.Column(db.Integer)

    DateStart = db.Column(db.DateTime, default=None)
    DateEnd = db.Column(db.DateTime, default=None)
    unit = db.relationship('Unit', backref='indicators')
    indicators_usage = db.relationship("IndicatorUsage", back_populates="indicator")

class IndicatorUsage(db.Model):
    __tablename__ = 'indicators_usage'
    id = db.Column(db.Integer, primary_key=True)
    id_indicator = db.Column(db.Integer, db.ForeignKey('indicators.id'), nullable=False)
    note = db.Column(db.String(), default=None, nullable=True)
    id_plan = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False)
    QYearBeforePrev = db.Column(Numeric(scale=2))
    QYearPrev = db.Column(Numeric(scale=2))
    QYearCurrent = db.Column(Numeric(scale=2))
    
    is_local = db.Column(db.Boolean, default=False)
    is_renewable = db.Column(db.Boolean, default=False)
    
    coeff_before_prev = db.Column(Numeric(scale=3), nullable=True)
    coeff_prev = db.Column(Numeric(scale=3), nullable=True)         
    coeff_current = db.Column(Numeric(scale=3), nullable=True)
    
    indicator = db.relationship("Indicator", back_populates="indicators_usage")
    plan = db.relationship("Plan", back_populates="indicators_usage")

    def get_coeff_for_year(self, year_type):
        base_coeff = self.indicator.CoeffToTut
        
        if year_type == 'before':
            return self.coeff_before_prev if self.coeff_before_prev is not None else base_coeff
        elif year_type == 'prev':
            return self.coeff_prev if self.coeff_prev is not None else base_coeff
        elif year_type == 'current':
            return self.coeff_current if self.coeff_current is not None else base_coeff
        return base_coeff

    def as_dict(self):
        return {
            'id': self.id,
            'id_indicator': self.id_indicator,
            'id_plan': self.id_plan,
            'QYearBeforePrev': self.QYearBeforePrev,
            'QYearPrev': self.QYearPrev,
            'QYearCurrent': self.QYearCurrent,
            'coeff_before_prev': self.coeff_before_prev,
            'coeff_prev': self.coeff_prev,
            'coeff_current': self.coeff_current,
            'CoeffToTut': self.get_coeff_for_year('current'),
            'name': self.indicator.name
        }
        
class StatPlan(db.Model):
    __tablename__ = "stat_plans"
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organization.id"), nullable=False)
    type = db.Column(db.String(10), nullable=False)   # '12-tek' | '4-tek'
    year = db.Column(db.Integer, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    uploaded_at = db.Column(db.DateTime)
    organization = db.relationship("Organization", backref="stat_plans")
    uploaded_by = db.relationship("User")
 
    values = db.relationship(
        "StatPlanValue",
        back_populates="stat_plan",
        lazy=True,
        cascade="all, delete-orphan",
    )
 
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "type", "year",
            name="uq_stat_plan_org_type_year",
        ),
    )
 
    def __repr__(self):
        return f"<StatPlan {self.type} {self.year} org={self.organization_id}>"
 
    def get_value(self, row_code, column_code):
        row_code, column_code = str(row_code), str(column_code)
        for v in self.values:
            if v.row_code == row_code and v.column_code == column_code:
                return v.value
        return None
 
class StatPlanValue(db.Model):
    __tablename__ = "stat_plan_values"
 
    id = db.Column(db.Integer, primary_key=True)
    stat_plan_id = db.Column(db.Integer, db.ForeignKey("stat_plans.id"), nullable=False)
 
    row_code = db.Column(db.String(20), nullable=False)
    row_name = db.Column(db.String(500))
    column_code = db.Column(db.String(10), nullable=False)
    value = db.Column(db.Numeric(scale=4))
 
    stat_plan = db.relationship("StatPlan", back_populates="values")
 
    __table_args__ = (
        UniqueConstraint(
            "stat_plan_id", "row_code", "column_code",
            name="uq_stat_value_cell",
        ),
    )
 
    def __repr__(self):
        return f"<StatPlanValue row={self.row_code} col={self.column_code} val={self.value}>"

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    is_user = db.Column(db.Boolean, nullable=False, default=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=current_utc_time)
    chat = db.relationship('Chat', foreign_keys=[chat_id], back_populates='messages')
    
    def __repr__(self):
        return f'<Message {self.id} in chat {self.chat_id}>'

class Chat(db.Model):
    __tablename__ = 'chats'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id], back_populates='created_chats')
    messages = db.relationship('ChatMessage',
                              back_populates='chat',
                              cascade='all, delete-orphan',
                              passive_deletes=True,
                              lazy='dynamic')
    created_at = db.Column(db.DateTime, nullable=False, default=current_utc_time)
    updated_at = db.Column(db.DateTime, nullable=False, default=current_utc_time, onupdate=current_utc_time)