from flask import Blueprint, render_template, request,redirect,url_for,jsonify
from flask_cors import CORS
import _json
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def homepage():
    return render_template('homepage.html')