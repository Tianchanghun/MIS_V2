"""
상품관리 모듈
"""
from flask import Blueprint

bp = Blueprint('product', __name__, url_prefix='/product')

from app.product import routes 