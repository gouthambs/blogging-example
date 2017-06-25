from flask import Flask, redirect, url_for, request, session
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_blogging import SQLAStorage, BloggingEngine
from flask_login import LoginManager, current_user, login_user
from flask_migrate import Migrate
from flask_misaka import Misaka
from flask_principal import Principal, UserNeed, RoleNeed, identity_loaded
from flask_sslify import SSLify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base

from config import config

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)

    migrate = Migrate()
    migrate.init_app(app, db=db)

    login_manager.session_protection = 'strong'
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    principal = Principal()
    principal.init_app(app)

    from app.models import User, Sentence, Quiz, Answer

    # Flask-Blogging database config
    with app.app_context():
        storage = SQLAStorage(db=db)
        db.create_all()
        blog_engine = BloggingEngine()
        blog_engine.init_app(app, storage)

    misaka = Misaka(
        app=None,
        renderer=None,
        strikethrough=True,
        underline=True,
        tables=True,
        wrap=True
    )
    misaka.init_app(app)

    from wtforms.fields import HiddenField

    def is_hidden_field_filter(field):
        return isinstance(field, HiddenField)

    app.jinja_env.globals['bootstrap_is_hidden_field'] = \
        is_hidden_field_filter

    # TODO: Move these auth handlers out of __init__.py
    @login_manager.user_loader
    # @blog_engine.user_loader
    def load_user(user_id):
        print "ID: ", user_id
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def handle_unauthorized():
        if session.get('_id'):
            return redirect(url_for('auth.login'))
        else:
            login_user(User().save())
            return redirect(request.url)

    @identity_loaded.connect_via(app)
    def on_identity_loaded(sender, identity):
        identity.user = current_user

        if hasattr(current_user, "id"):
            identity.provides.add(UserNeed(current_user.id))

        # Shortcut to the give admins "blogger" role.
        if hasattr(current_user, "is_admin"):
            if current_user.is_admin:
                identity.provides.add(RoleNeed("blogger"))


    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')


    # Initialise flask-admin
    admin = Admin(
        app,
        template_mode='bootstrap3',
        index_view=AdminIndexView()
    )
    Post = storage.post_model
    # Add administrative views here
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Post, db.session))

    return app
