import json
import os
from re import L
import jwt
import numpy as np
import pandas as pd
from flask import Flask
from flask.helpers import send_from_directory
from flask_cors import CORS, cross_origin
from flask import request, jsonify, Response, g, current_app, send_file
from werkzeug.utils import secure_filename
from functools import wraps
from api_test.service import ocr_service, user_service



def login_required(f):
    @wraps(f)
    def decorated_function(*arg, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(
                    access_token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                payload = None
            if payload is None:
                return Response(status=401)
            user_id = payload['user_id']

            if user_id is not None:

                g.user_id = user_id
            else:
                return Response(status=403)
        else:
            return Response(status=401)

        return f(*arg, **kwargs)
    return decorated_function

def create_endpoints(app,service):
    
    user_service = service.user_service
    ocr_service = service.ocr_service

    #api서버의 운행여부를 체크하는 엔드포인드 - health check   
    @app.route("/ping", methods=["GET"])
    def ping():
        return "pong"

    #회원가입 - 완료
    @app.route('/sign-up', methods=('POST', 'OPTION'))
    def sign_up():
        try:
            # 프론트로 부터 받은 json데이터를 변수에 저장
            new_user = request.json

            create_user = user_service.create_new_user(new_user) 

            if create_user == "length_error":
                return "length_error",403

            elif create_user is None:
                return "sign up fail"
            
            elif create_user == "success":
                return "회원가입 성공!", 200

        except Exception as ex:
            return 'id_error',401
        
        return "회원가입 성공!", 200


    # 로그인을 위한 엔드포인트-완료
    @app.route('/sign-in', methods=['POST', 'OPTION'])
    def sign_in():
        credential = request.json
        
        authorized = user_service.sign_in(credential)


        if authorized == 'not_id':
            return 'not_id',401
        
        elif authorized is None:
            return 'password_error',401
        
        else:
            user_credential = user_service.get_user_id_passwd(credential['user_id'])
            user_id = user_credential["user_id"]
            token = user_service.generate_access_token(user_id)
        
            return json.dumps({'access_token': token})

    # 템플릿을 추가하는 엔드포인트 - 템플릿을 추가하면 프론트에서 바로 템플릿 리스트 업데이트를 위해서 디비에 추가후 다시 불러와서 템플릿명을 리턴해줌-테스트완료
    @app.route('/template-add', methods=['POST', 'OPTION'])
    @login_required
    def template_add():
        new_template = request.json
        new_template['user_id'] = g.user_id

        template_add_name = user_service.template_add_service(new_template)
        if template_add_name is None:
            return "template_add_fail",404

        return template_add_name


    # 템플릿 이름으로 좌표 찾기 - 완료
    @app.route('/template-value', methods=['POST', 'OPTION'])
    @login_required
    def template_find():
        template_name = request.json
        template_name['user_id'] = g.user_id

        template_info = user_service.template_find_service(template_name)

        if template_info == "not_found_table" or template_info is None:
            return "not found table",400
        
        elif template_info == "not_found_file":
            return "File is missing",404

        else:
            return template_info


    # 템플릿 이름 전체 조회 - 완료
    @app.route('/template-all-name', methods=('GET', 'OPTION'))
    @login_required
    def template_all_name():
        template_all_name_result = user_service.template_all_name_service(g.user_id)

        if template_all_name_result is None:
            return "not found table",400
        
        else:
            return template_all_name_result


    # 템플릿 수정 - id를 통해서 수정 - 완료
    @app.route('/template-update', methods=('POST', 'OPTION'))
    @login_required
    def template_update():
        template_update_info = request.json

        #서비스 레이어에 값 넘기고 결과 받기
        template_update_result = user_service.template_update_service(template_update_info,g.user_id)

        if template_update_result == False:
            return "update fail", 404

        else:
            return "update success",200
    
    # 템플릿 전체 삭제 - 완료
    @app.route('/template-del', methods=('POST', 'OPTION'))
    @login_required
    def template_del():
        template_del_name = request.json
        template_del_name['user_id'] = g.user_id

        template_del_service_result = user_service.template_del_service(template_del_name)

        if template_del_service_result == False:
            return "delete fail",404
        
        else:
            return "delete success",200

    # 템플릿 ocr - 완료
    @app.route('/template-ocr/<ocr_type>', methods=('POST', 'OPTION'))
    @login_required
    def template_ocr_result(ocr_type):

        template_information = request.json

        if template_information['image'] is None:
            return "not found image",400

        template_ocr_service_result = ocr_service.template_ocr_service(template_information,ocr_type,g.user_id)

        if template_ocr_service_result is None:
            return Response(status=404)
        
        elif template_ocr_service_result == "type_error":
            return "type error",404
        
        else:
            return json.dumps(template_ocr_service_result)

    #템플릿 ocr에서 필드명과 텍스트 결과로 엑셀파일 만들기(xlsx로 만듦 , 컬럼은 필드명으로) - 완료
    @app.route('/template-ocr-excel',methods=('POST','OPTION'))
    @login_required
    def template_ocr_excel():
        template_result_info = request.json

        #엑셀 저장하는 서비스 로직에서 파일 경로 반환
        template_ocr_excel_service_result = ocr_service.template_result_info_service(template_result_info,g.user_id)
        
        if template_ocr_excel_service_result is None:
            return "file download fail",404
        else:
            return send_file(template_ocr_excel_service_result)

    # 이미지에서 테이블을 검출하는 엔드포인트 - 완료
    @app.route('/table-find', methods=('POST', 'OPTION'))
    @login_required
    def find_table():

        if 'file' not in request.files:
            return 'File is missing', 404

        req = request.files.getlist("file")

        table_find_service_result = ocr_service.table_find_service(g.user_id,req)

        if table_find_service_result == "not_found_table":
            return "not found table", 204
        
        elif table_find_service_result is None:
            return Response(status=404)

        else:
            return json.dumps(table_find_service_result),200


    # 검출된 테이블을 엑셀로 변환후 리턴 - POST로 검출한 테이블 사진을 받아서 엑셀 변환 - 완료
    @app.route('/table-result-download', methods=('GET', 'OPTION'))
    @login_required
    def table_result_download():

        table_result_download_service_result = ocr_service.table_result_download_service(g.user_id)

        if table_result_download_service_result is None:
            return None
        else:
            return send_file(table_result_download_service_result)


    # 전체 ocr - 테스트완료
    @app.route('/normal-all-ocr/<ocr_type>', methods=('GET', 'POST', 'OPTION'))
    def normal_all(ocr_type):
        if 'file' not in request.files:
            return 'File is missing', 404

        req = request.files.getlist('file')

        normal_all_ocr_service_result = ocr_service.normal_all_ocr_service(req,int(ocr_type))

        if normal_all_ocr_service_result is None:
            return Response(status=404)

        elif normal_all_ocr_service_result == "type_error":
            return "type error",404

        else:
            return json.dumps(normal_all_ocr_service_result)

