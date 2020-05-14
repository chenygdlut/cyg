# -*- coding: utf-8 -*-
import html
import hashlib
from random import randint
from datetime import datetime
from . import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app, request, url_for, abort
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach


@login_manager.user_loader
def load_user(user_id):
    """使用flask_login时必须实现的函数 返回None或者实例"""
    if int(user_id) == 1:
        return Administrator.query.get(int(user_id))
    if int(user_id) >= 999:
        return User.query.get(int(user_id))
    return None



class AnonymousUser(AnonymousUserMixin):
    """匿名用户类"""
    def can(self):
        return False

    def is_administrator(self):
        return False

    def get_names(self):
        return []


login_manager.anonymous_user = AnonymousUser


class Administrator(UserMixin, db.Model):
    """管理员表 整个网站只设置一个管理员账号, 需要在命令行手动注册"""

    __tablename__ = 'administrator'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), nullable=False, unique=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=True)

    @property
    def password(self):
        raise AttributeError("这不是一个可读属性")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """验证密码，返回布尔值"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def register_admin():
        """注册管理员账号"""
        db.create_all()
        only_admin = Administrator(username=current_app.config['ADMIN_USERNAME'])
        only_admin.password = current_app.config['ADMIN_PASSWORD']
        db.session.add(only_admin)
        db.session.commit()

    def get_names(self):
        names = []
        for name in SecondPageName.query.all():
            names.append((name.page_name, name.url))
        return names

    @staticmethod
    def is_user():
        return False


class User(db.Model, UserMixin):
    """用户模版
        有一个默认的协助管理账户 id为999 这样用户注册时最小id即为1000
        管理者有权限删除留言
        删除留言后 在用户的通知信息中 显示信息
    """
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar()

    # 头像hash
    avatar_hash = db.Column(db.Text)

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # 是否是管理员
    is_admin = db.Column(db.Boolean, default=False)
    # 禁用日期
    disable_time = db.Column(db.DateTime)
    # 接收的信息
    infos = db.relationship("Info", backref='user', lazy='dynamic')
    # 必填
    username = db.Column(db.String(32), unique=True, nullable=True)
    email = db.Column(db.String(32), unique=True, nullable=True)
    password_hash = db.Column(db.String(128))
    # 选填
    name = db.Column(db.String(16))
    phone = db.Column(db.Integer)
    # 昵称
    nickname = db.Column(db.String(32))
    # 1是男性 2女 3待定
    male = db.Column(db.Integer)
    age = db.Column(db.Integer)
    tops = db.Column(db.Integer)
    weight = db.Column(db.Integer)
    position = db.Column(db.String(16))
    about_me = db.Column(db.Text)
    qq = db.Column(db.Integer)
    WeChat = db.Column(db.String(16))
    confirmed = db.Column(db.Boolean, default=False)
    
    @staticmethod
    def is_user():
        return True

    @property
    def password(self):
        raise AttributeError("这不是一个可读属性")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """验证密码，返回布尔值"""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def is_position(value):
        """检验值是否是三个位置中的一个, 可删减"""
        positions = ['后卫', '前锋', '中锋']
        if value in positions:
            return True
        return False

    @staticmethod
    def default_user():
        """自动注册一个id为999的管理者， 之后注册的用户id从1000开始"""
        user = User(id=999, is_admin=True,
                    email=current_app.config['ADMIN_USERNAME'],
                    username='管理员', confirmed=True)
        user.password = current_app.config['ADMIN_PASSWORD']
        db.session.add(user)
        db.session.commit()

    def generate_confirmation_token(self, expiration=3600):
        """生成一个验证用token 持续时间为1天"""
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        """验证token的值"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def get_info(self):
        """返回用户收到的信息"""
        return {'info': self.infos}

    def to_json(self):
        """返回一个json"""
        json_data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'phone': self.phone,
            'qq': self.qq,
            'WeChat': self.WeChat,
            'name': self.name,
            'nickname': self.nickname,
            'male': self.male,
            'age': self.age,
            'tops': self.tops,
            'weight': self.weight,
            'position': self.position,
            'about_me': self.about_me,
            'avatar_hash': self.avatar_hash
        }
        return json_data

    def easy_to_json(self):
        """返回不保密的用户信息"""
        json_data = {
            'id': self.id,
            'username': self.username,
            'avatar_hash': self.avatar_hash,
            'nickname': self.nickname,
            'position': self.position,
            'about_me': self.about_me,
            'auth_url': url_for('auth.index', id=self.id)
        }
        return json_data

    @staticmethod
    def from_json(data):
        id = data.get('id')
        if id is not None:
            user = User.query.get_or_404(id)
        else:
            user = User()
            user.username = data.get('username')
            user.email = data.get('email')
            user.password = data.get('password')
        user.avatar_hash = data.get('avatar') or user.gravatar()
        user.phone = data.get('phone')
        user.qq = data.get('qq')
        user.WeChat = data.get('WeChat')
        user.name = data.get('name')
        user.nickname = data.get('nickname')
        user.male = int(data.get('gender'))
        user.age = data.get('age')
        user.tops = data.get('tops')
        user.weight = data.get('weight')
        user.about_me = data.get('about_me')
        if user.is_position(data.get('position')):
            user.position = data.get('position')
        return user

    
    def gravatar(self, size=128, default='identicon', rating='g'):
        """使用gravatar生成用户头像"""
        if self.avatar_hash is not None:
            return self.avatar_hash
        if request.is_secure:  # 如果响应是安全的
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        my_hash = hashlib.md5(self.email.encode(
            'utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=my_hash, size=size, default=default, rating=rating
        )

    @staticmethod
    def get_user_id(token):
        """通过token获取用户id"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return data.get('confirm')


class Info(db.Model):
    """用户接受的信息"""
    __tablename__ = 'info'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow())

    def to_json(self):
        json_data = {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message
        }
        return json_data

    @staticmethod
    def from_json(data):
        return Info(user_id=data.get('user_id'), message=data.get('message'))

    def read(self):
        """改变状态为已读"""
        self.is_read = True
        db.session.add(self)


class Bilu(db.Model):
    """笔录模版"""
    __tablename__ = 'bilus'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(32), default='标题')
    body = db.Column(db.Text)
    act_date = db.Column(db.DateTime, index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow())

    def to_json(self, brief=False):
        json_data = {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'act_date': datetime.strftime(self.act_date, '%Y-%m-%d'),
            'timestamp': self.timestamp,
            'api_url': url_for('api.delete_bilu', id=self.id),
            'edit_url': url_for('manage.edit_bilu',
                                id=self.id, _external=True),
        }
        if brief:
            json_data.pop('body')
        return json_data

    @staticmethod
    def from_json(json_data):
        id = json_data.get('id')
        if id is not None:
            obj = Bilu.query.get_or_404(id)
        else:
            obj = Bilu()
        obj.title = json_data.get('title')
        obj.body = json_data.get('body')
        obj.act_date = datetime.strptime(json_data.get(
            'act_date'), '%Y-%m-%d')
        return obj

#测试 
# def test():
#     db.reflect()
#     all_table = {table_obj.name: table_obj for table_obj in db.get_tables_for_bind()}
#     a = db.session.query(all_table["city"]).all
#     return [x._asdict() for x in a]
# class City(db.Model):
#     ID=db.Column(db.Integer, primary_key=True)
#     Name=db.Column(db.String(35),nullable=False,default='')
#     CountryCode=db.Column(db.String(3),nullable=False,default='')
#     District=db.Column(db.String(20),nullable=False,default='')
#     Population=db.Column(db.Integer,nullable=False,default='0')

class comment_info(db.Model):
    '''批注信息表'''
    #案件编号,外键
    low_case_num=db.Column(db.VARCHAR(128),nullable=False)
    #批注编号，主键
    comment_num = db.Column(db.VARCHAR(128), nullable=False,primary_key=True)
    #批注实体类型
    comment_entity_type = db.Column(db.CHAR(1), nullable=False)
    #批注实体编号
    comment_entity_num = db.Column(db.VARCHAR(128), nullable=False)
    #批注内容
    comment_text = db.Column(db.TEXT(), nullable=False)

    #记录
    record_status = db.Column(db.CHAR(1), nullable=False)
    create_datetime = db.Column(db.TIMESTAMP(), nullable=False)
    create_by = db.Column(db.VARCHAR(128), nullable=False)
    update_datetime = db.Column(db.TIMESTAMP(), nullable=False)
    update_by = db.Column(db.VARCHAR(128), nullable=False)

    def to_json(self, brief=False):
        json_data = {
            'low_case_num':self.low_case_num,
            'comment_num':self.comment_num,
            'comment_entity_type':self.comment_entity_type,
            'comment_entity_num':self.comment_entity_num,
            'comment_text':self.comment_text,
            'record_status': self.record_status,
            'create_datetime': self.create_datetime,
            'create_by': self.create_by,
            'update_datetime': self.update_datetime,
            'update_by': self.update_by,
        }

    @staticmethod
    def fom_json(self,json_data):
        comment_num = json_data.get('comment_num')
        if(comment_num is not None):
            obj = comment_info.query.get_or_404(comment_num)
        else:
            obj = comment_info()
        obj.low_case_num=json_data.get('low_case_num')
        obj.comment_num = json_data.get('comment_num')
        obj.comment_entity_type = json_data.get('comment_entity_type')
        obj.comment_entity_num = json_data.get('comment_entity_num')
        obj.comment_text = json_data.get('comment_text')
        obj.record_status = json_data.get('record_status')
        obj.create_datetime = json_data.get('create_datetime')
        obj.create_by = json_data.get('create_by')
        obj.update_datetime = json_data.get('update_datetime')
        obj.update_by = json_data.get('update_by')
        return obj

class law_case_info(db.Model):
    '''案件信息表'''
    #案件编号
    low_case_num = db.Column(db.VARCHAR(128), nullable=False,primary_key=True)
    #案件原由
    low_case_reason=db.Column(db.VARCHAR(128), nullable=False)
    #当事人
    low_case_party=db.Column(db.VARCHAR(64), nullable=False)
    #案例事实
    low_case_content=db.Column(db.TEXT(), nullable=False)
    #审批法院
    low_case_court = db.Column(db.TEXT(), nullable=False)
    #判决时间
    low_case_decision_time=db.Column(db.TIMESTAMP(), nullable=False)
    #执行法官编号
    low_case_executive_judge=db.Column(db.VARCHAR(64), nullable=False)
    #辩护律师编号
    low_case_defence_counsel=db.Column(db.VARCHAR(64), nullable=False)
    #案件名称
    low_case_name=db.Column(db.VARCHAR(128), nullable=False)
    #记录
    record_status = db.Column(db.CHAR(1), nullable=False)
    create_datetime = db.Column(db.TIMESTAMP(), nullable=False)
    create_by = db.Column(db.VARCHAR(128), nullable=False)
    update_datetime = db.Column(db.TIMESTAMP(), nullable=False)
    update_by = db.Column(db.VARCHAR(128), nullable=False)

    def to_json(self, brief=False):
        json_data={
            'low_case_num':self.low_case_num,
            'low_case_reason':self.low_case_reason,
            'low_case_party':self.low_case_party,
            'low_case_court':self.low_case_court,
            'low_case_decision_time':self.low_case_decision_time,
            'low_case_executive_judge':self.low_case_executive_judge,
            'low_case_defence_counsel':self.low_case_defence_counsel,
            'low_case_name':self.low_case_name,
            'record_status':self.record_status,
            'create_datetime':self.create_datetime,
            'create_by':self.create_by,
            'update_datetime':self.update_datetime,
            'update_by':self.update_by,
        }
        return json_data

    @staticmethod
    def queryBy_low_case_num(key):
        m=law_case_info.query.filter_by(low_case_num=key).first()
        return m.to_json()

    @staticmethod
    def fom_json(json_data):
        low_case_num=json_data.get('low_case_num')
        if(low_case_num is not None):
            obj = law_case_info.query.get_or_404(low_case_num)
        else:
            obj = law_case_info()
        obj.low_case_reason = json_data.get('low_case_reason')
        obj.low_case_party = json_data.get('low_case_party')
        obj.low_case_court = json_data.get('low_case_court')
        obj.low_case_decision_time = json_data.get('low_case_decision_time')
        obj.low_case_executive_judge = json_data.get('low_case_executive_judge')
        obj.low_case_defence_counsel = json_data.get('low_case_defence_counsel')
        obj.low_case_name = json_data.get('low_case_name')
        obj.record_status = json_data.get('record_status')
        obj.create_datetime = json_data.get('create_datetime')
        obj.create_by = json_data.get('create_by')
        obj.update_datetime = json_data.get('update_datetime')
        obj.update_by = json_data.get('update_by')
        return obj

    @staticmethod
    def insert(m):
        db.session.add(m)
        db.session.commit()

class indictment_bill_info(db.Model):
    """起诉意见书管理"""
    # __tablename__ = 'indictment_bill_info'
    # id = db.Column(db.Integer, primary_key=True)
    # 案件编号
    low_case_num = db.Column(db.VARCHAR(128), db.ForeignKey('law_case_info.low_case_num'), index=True,nullable=False)
    # 文书编号
    bill_num = db.Column(db.VARCHAR(128),nullable=False,index=True,primary_key=True)
    # 原告
    bill_plaintiff = db.Column(db.TEXT(),nullable=False)
    # 被告
    bill_demandant = db.Column(db.TEXT(),nullable=False)
    # 第三人
    bill_third_party  = db.Column(db.TEXT(),nullable=True)
    # 起诉人
    bill_prosecutor = db.Column(db.VARCHAR(128),nullable=False)
    #诉讼请求
    bill_claim = db.Column(db.TEXT(),nullable=False)
    # 事实与理由
    bill_fact_and_reason = db.Column(db.TEXT(),nullable=False)

    # 记录
    record_status = db.Column(db.CHAR(1),nullable=False,default='1')
    create_datetime = db.Column(db.TIMESTAMP(),nullable=False)
    create_by = db.Column(db.VARCHAR(64))
    update_datetime = db.Column(db.TIMESTAMP() ,nullable=False)
    update_by = db.Column(db.VARCHAR(64),nullable=False)

    def to_json(self, brief=False):
        json_data = {
            'low_case_num':self.low_case_num,
            'bill_num':self.bill_num,
            'bill_plaintiff':self.bill_plaintiff,
            'bill_demandant':self.bill_demandant,
            'bill_third_party':self.bill_third_party,
            'bill_prosecutor':self.bill_prosecutor,
            'bill_claim':self.bill_claim,
            'bill_fact_and_reason':self.bill_fact_and_reason,
            'record_status':self.record_status,
            'create_datetime':self.create_datetime,
            'create_by':self.create_by,
            'update_datetime':self.update_datetime,
            'update_by':self.update_by,
        }
        return json_data

    @staticmethod
    def queryBy_low_case_num(key):
        m=indictment_bill_info.query.filter_by(bill_num=key).first()
        return m.to_json()

    @staticmethod
    def from_json(json_data):
        bill_num = json_data.get('bill_num')
        if bill_num is not None:
            obj = indictment_bill_info.query.get_or_404(bill_num)
        else:
            obj = indictment_bill_info()
        obj.low_case_num  = json_data.get('low_case_num')
        obj.bill_plaintiff = json_data.get('bill_plaintiff')
        obj.bill_demandant = json_data.get('bill_demandant')
        obj.bill_third_party = json_data.get('bill_third_party')
        obj.bill_prosecutor = json_data.get('bill_prosecutor')
        obj.bill_claim = json_data.get('bill_claim')
        obj.bill_fact_and_reason = json_data.get('bill_fact_and_reason')
        obj.record_status = json_data.get('record_status')
        obj.create_datetime = json_data.get('create_datetime')
        obj.create_by = json_data.get('create_by')
        obj.update_datetime = json_data.get('update_datetime')
        obj.update_by = json_data.get('update_by')
        return obj

    @staticmethod
    def insert(m):
        db.session.add(m)
        db.session.commit()
