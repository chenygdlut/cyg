# -*- coding: utf-8 -*-

import json

from flask import url_for, render_template, redirect, request, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user

from . import manage
from .forms import AdminLoginForm
from ..models import Administrator,User,Bilu
from ..decorators import super_admin_required

from ..backend.matching import matching

@manage.route('/')
@login_required
@super_admin_required
def index():
    """管理页面首页"""
    users = User.query.all()
    user_num = len(users)
    return render_template('admin/index.html', user_num=user_num )


@manage.route('/login', methods=["POST", "GET"])
def login():
    """管理系统登录页面"""
    admin = Administrator.query.first()
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Administrator.query.filter_by(username=form.username.data).first()
        if admin is not None and admin.verify_password(form.password.data):
            login_user(admin)
            return redirect(request.args.get('next') or url_for('manage.index'))
        flash('用户名或密码错误！')
    return render_template('admin/login.html', form=form)


@manage.route('/logout')
@login_required
@super_admin_required
def logout():
    """管理系统登出"""
    logout_user()
    flash('退出成功')
    return redirect(url_for('manage.login'))


@manage.route('/bilus')
@login_required
@super_admin_required
def show_bilus():
    """显示笔录页面"""
    return render_template('admin/bilus.html')    


@manage.route('/new-bilu')
@login_required
@super_admin_required
def new_bilu():
    """新建一个笔录"""
    obj = Bilu()
    return render_template('admin/new-bilu.html',bilu=obj)


@manage.route('/bilu/<int:id>')
@login_required
@super_admin_required
def edit_bilu(id):
    """修改笔录"""
    obj = Bilu.query.get_or_404(id)
    return render_template('admin/edit-bilu.html', bilu=obj)

@manage.route('/qisushuAnalyzing')
@login_required
@super_admin_required
def qisushuAnalyzingPage():
    return render_template("admin/qisushuAnalyzing/qisushuAnalyzing.html")

@manage.route('/qisushuAnalyzing/timeline')
@login_required
@super_admin_required
def timeline():
    with open("app/demodata/timeline.json",'r',encoding="utf-8")as f:
        data = f.read()
    return jsonify(data)

@manage.route('/qisushuAnalyzing/text')
@login_required
@super_admin_required
def text():
    with open("app/demodata/text.json",'r',encoding="utf-8")as f:
        data = f.read()
    return jsonify(data)


###笔录分析###
@manage.route('/biluAnalyzing/text')
@login_required
@super_admin_required   
def main():
    with open("app/demodata/bilu/biludata.json", encoding="utf-8")as f:
        data = json.load(f)
    print(data)
    return render_template("admin/biluAnalyzing/web.html",data=data['biludata'][1])

@manage.route('/biluAnalyzing/bilutxt',methods=["GET"])
@login_required
@super_admin_required
def bilutxt():
    print(request.method)
    index = request.args.get("id")
    if index != None :
        
        print(index)
        with open("app/demodata/bilu/biludata.json", encoding="utf-8")as f:
            data = json.load(f)
        print(data['biludata'][2][str(index)])
        return render_template("admin/biluAnalyzing/bilutext.html",data= data['biludata'][2][str(index)])
    else:
        with open("app/demodata/bilu/biludata.json", encoding="utf-8")as f:
            data = json.load(f)
        return render_template("admin/biluAnalyzing/bilutext.html",data=data['biludata'][2]['1'])
        
@manage.route('/biluAnalyzing/qisutxt')
@login_required
@super_admin_required
def qisutxt():
    with open("app/demodata/bilu/biludata.json", encoding="utf-8")as f:
        data = json.load(f)
    return render_template("admin/biluAnalyzing/qisutext.html",data=data['biludata'][0]['originaltxt'])

#调试用代码
@manage.route('/hello')
def hello():
    from ..models import law_case_info
    info=law_case_info.queryBy_low_case_num('信检公诉刑诉〔2019〕298号')
    return str(info)

@manage.route('/hello2')
def hello2():
    from ..models import law_case_info
    import random
    info=law_case_info.queryBy_low_case_num('信检公诉刑诉〔2019〕298号')
    info['update_by']='hello_%d'%(random.randint(1,10))
    m=law_case_info.fom_json(info)
    law_case_info.insert(m)
    return '修改成功'

#调试查询起诉意见书表
@manage.route('/qisuyijianshubiao')
def helloworld():
    from ..models import indictment_bill_info
    m=indictment_bill_info.query.filter_by(bill_num='(2017)苏0492刑初235号').first()
    return str(m.to_json())