from flask import Flask
from flask_cors import CORS, cross_origin
from api_test.service import UserService,OcrService
from api_test.models import UserDao
from view import create_endpoints
from sqlalchemy import create_engine
import config
import os


#service클래스의 의존관계 정보를 담아서 view쪽으로 넘기기 위한 클래스
class Service:
    pass

#의존성 주입 가능하도록함
def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)

    if test_config is None:
        app.config.from_pyfile("config.py")
        # 이미지와 테이블이 저장될 폴더 생성
        if not os.path.exists(os.getcwd()+'/api_test/imagedir'):
            os.makedirs(os.getcwd()+'/api_test/imagedir/table_temp')
    else:
        app.config.update(test_config)

    database = create_engine(
        app.config['DB_URL'], encoding='utf-8', max_overflow=0)

    # 이미지와 테이블이 저장될 폴더 생성
    if not os.path.exists(os.getcwd()+'/api_test/imagedir'):
        os.makedirs(os.getcwd()+'/api_test/imagedir/table_temp')

    #Persistence Layer 객체
    user_dao = UserDao(database)

    #Business layer 객체들
    service = Service
    service.user_service = UserService(user_dao,app.config)
    service.ocr_service = OcrService(app.config)

    create_endpoints(app,service)

    return app
