from flask import Flask
from flask.helpers import send_from_directory
from flask_cors import CORS, cross_origin
from flask import request, jsonify, Response, g, current_app, send_file
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text


from datetime import datetime, timedelta
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from functools import wraps

from pdf2image import convert_from_path

import json
import os
import shutil

import cv2
import pytesseract
import numpy as np
import pandas as pd

import jwt  # Json web token
import bcrypt
import base64
import yolov5

import api_test.table_find as tab
import api_test.table_processing as proc
import sys

import openpyxl




# 인증을 위한 데코레이터 함수 - 이 데코레이터 함수를 적용하면 각 엔드포인트의 함수를 실행하기 전에 이 함수를 실행하게 된다.
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
            g.user_id = user_id
            # g.user = get_user_info(user_id) if user_id else None => 디비에서 user_id를 통해서 정보를 가져옴
        else:
            return Response(status=401)

        return f(*arg, **kwargs)
    return decorated_function


def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app)

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update("test_config")

    database = create_engine(
        app.config['DB_URL'], encoding='utf-8', max_overflow=0)
    app.database = database

    # 이미지와 테이블이 저장될 폴더 생성
    if not os.path.exists(os.getcwd()+'/api_test/imagedir'):
        os.makedirs(os.getcwd()+'/api_test/imagedir/table_temp')

    # 회원가입을 위한 엔드포인트-테스트완료
    @app.route('/sign-up', methods=('POST', 'OPTION'))
    def sign_up():
        if request.method == 'POST':
            try:
                # print('check ----------------------------------------------------------')
                new_user = request.json  # 프론트로 부터 받은 json데이터를 변수에 저장
                print(new_user)

                if len(new_user['user_id']) < 1 or len(new_user['passwd']) < 1 or len(new_user['user_email']) < 1:
                    return "length_error",403

                # 단방향 해쉬(그중 bcrypt 알고리즘을 이용)를 이용해서 비밀번호 암호화
                # hashpw=>인자로 바이트 value을 받기 떄문에 인코딩 해준다.
                new_user['passwd'] = bcrypt.hashpw(
                    new_user['passwd'].encode('UTF-8'), bcrypt.gensalt())
                # print(new_user)
                new_user_id = app.database.execute(text(
                    """INSERT INTO users(user_id,user_email,passwd) VALUES(:user_id,:user_email,:passwd)"""), new_user).lastrowid

                #row = app.database.execute(text("""SELECT user_id,user_email,passwd FROM users WHERE user_id=:req_id"""),{'req_id':new_user_id}).fetchone()
                # reated_user={
                #    'user_id':row['user_id'],
                #    'user_email':row['user_email'],
                #    'passwd':row['passwd']
                # } if row else None
            except Exception as ex:
                return 'id_error',401
            return "회원가입 성공!", 200


    # 로그인을 위한 엔드포인트-테스트완료
    @app.route('/sign-in', methods=['POST', 'OPTION'])
    def sign_in():
        if request.method == 'POST':
            credential = request.json
            user_id = credential['user_id']
            passwd = credential['passwd']

            row = database.execute(text("""SELECT passwd FROM users WHERE user_id = :user_id"""), {'user_id': user_id}).fetchone()
            #없는 아이디일때 - 토큰이 None 
            if row == None:
                return 'not_id',401
            # row => None이면 인증할 필요가 없음, bcrypt.checkpw=> 두 인자를 받아서 비교하여 같으면 Ture 다르면 False
            if row and bcrypt.checkpw(passwd.encode('UTF-8'), row['passwd'].encode('UTF-8')):
                # 아이디 값을 받아서 템플릿 테이블 조회해서 템플릿 명 전부 가져와서 json으로 만들고 페이로드에 담기
                # exp는 유효기간을 말함(jwt 즉 토큰의 유효기간)
                payload = {
                    'user_id': user_id,
                    'exp': datetime.utcnow()+timedelta(seconds=60*60*24)
                }
                token = jwt.encode(
                    payload, app.config['JWT_SECRET_KEY'], 'HS256')
                
                
                return jsonify({'access_token': token})
            else:
                return 'password_error', 401

    # 템플릿을 추가하는 엔드포인트 - 템플릿을 추가하면 프론트에서 바로 템플릿 리스트 업데이트를 위해서 디비에 추가후 다시 불러와서 템플릿명을 리턴해줌-테스트완료
    @app.route('/template-add', methods=['POST', 'OPTION'])
    @login_required
    def template_add():
        if request.method == 'POST':
            new_template = request.json
            #new_template['user_id'] = g.user_id

            f_path2 = app.config['IMAGE_PATH']+"/user_info"

            filename = new_template['template_name']
            
            if not os.path.isdir(f_path2):
                os.mkdir(f_path2)

            f_path = app.config['IMAGE_PATH']+"/user_info/"+g.user_id
            if not os.path.isdir(f_path):
                os.mkdir(f_path)

            # 받은 인코딩된 값을 디코딩하고 저장
            image_decode = base64.b64decode(new_template['image'])
            image_save_path = f_path+"/"+new_template['template_name']+".png"
            if not os.path.isfile(image_save_path):
                with open(image_save_path, 'wb') as f:
                    f.write(image_decode)

            # 이미 있으면 삭제하고 생성
            else:
                os.remove(image_save_path)
                with open(image_save_path, 'wb') as f:
                    f.write(image_decode)

            # 디비에 저장하기 위해서 만듦
            for i in new_template['template_info']:
                i['user_id'] = g.user_id
                i['template_name'] = new_template['template_name']
                i['image_path'] = image_save_path

                new_template_name = app.database.execute(text("""
                INSERT INTO ocr_template(
                    user_id,
                    template_name,
                    item_name,
                    start_x,
                    start_y,
                    stop_x,
                    stop_y,
                    image_path
                    ) VALUES(:user_id,:template_name,:item_name,:start_x,:start_y,:stop_x,:stop_y,:image_path
                    )"""), i).lastrowid

            row = app.database.execute(text("""SELECT template_name FROM ocr_template WHERE id=:req_id"""), {'req_id': new_template_name}).fetchone()
            # sent_template_name={
            #    'template_name':row['template_name']
            # } if row else None

            return row['template_name']

    # 템플릿 이름으로 좌표 찾기-테스트 완료
    @app.route('/template-value', methods=['POST', 'OPTION'])
    @login_required
    def template_find():
        if request.method == 'POST':
            template_name = request.json
            template_name['user_id'] = g.user_id

            try:

                rows = app.database.execute(text("""
                SELECT
                id,
                item_name,
                start_x,
                start_y,
                stop_x,
                stop_y,
                image_path 
                FROM ocr_template
                WHERE user_id= :user_id AND template_name=:template_name
                """), template_name).fetchall()
                
                if rows is None:
                    return None
                    
            except:
                return "not found table",400

            

            temp = {}
            
            template_value = [{
                'id': row['id'],
                'item_name': row['item_name'],
                'start_x': row['start_x'],
                'start_y': row['start_y'],
                'stop_x': row['stop_x'],
                'stop_y': row['stop_y']
            } for row in rows]

            img_path = rows[0]['image_path']
            if os.path.isfile(img_path):
                with open(img_path, 'rb') as im:
                    send_image = base64.b64encode(im.read()).decode('utf8')
            else:
                return "File is missing", 404

            return_value = {'template_name': template_name['template_name'],
                            'template_info': template_value, 'image': send_image, 'image_path': img_path}
            return json.dumps(return_value)

    # 템플릿 이름 전체 조회 - 테스트완료
    @app.route('/template-all-name', methods=('GET', 'OPTION'))
    @login_required
    def template_all_name():
        if request.method == 'GET':
            rows = app.database.execute(text("""
            SELECT
            template_name
            FROM ocr_template
            WHERE user_id= :user_id
            """), {"user_id": g.user_id}).fetchall()

            template_name = set([row['template_name'] for row in rows])


            temp = {}
            temp["template_name_list"] = list(template_name)
        return json.dumps(temp)

    # 템플릿 수정 - id를 통해서 수정
    @app.route('/template-update', methods=('POST', 'OPTION'))
    @login_required
    def template_update():
        if request.method == 'POST':
            template_update_info = request.json
            # 기존것 수정
            if template_update_info["edit"]:
                # if "edit" in template_update_info.keys():
                for i in template_update_info['edit']:
                    i['user_id'] = g.user_id
                    i['template_name'] = template_update_info['template_name']

                    i['start_x'] = int(i['start_x'])
                    i['start_y'] = int(i['start_y'])
                    i['stop_x'] = int(i['stop_x'])
                    i['stop_y'] = int(i['stop_y'])

                    app.database.execute(text("""
                    UPDATE ocr_template 
                    SET template_name=:template_name,item_name=:item_name,start_x=:start_x,start_y=:start_y,stop_x=:stop_x,stop_y=:stop_y 
                    WHERE id=:id AND user_id=:user_id"""), i)

            # 새로운 좌표 추가
            if template_update_info["add_edit"]:
                # if "add_edit" in template_update_info.keys():
                for j in template_update_info['add_edit']:
                    j['user_id'] = g.user_id
                    j['template_name'] = template_update_info['template_name']
                    j['image_path'] = template_update_info['image_path']

                    j['start_x'] = int(j['start_x'])
                    j['start_y'] = int(j['start_y'])
                    j['stop_x'] = int(j['stop_x'])
                    j['stop_y'] = int(j['stop_y'])

                    app.database.execute(text("""
                    INSERT INTO ocr_template(
                    user_id,
                    template_name,
                    item_name,
                    start_x,
                    start_y,
                    stop_x,
                    stop_y,
                    image_path
                    ) VALUES(:user_id,:template_name,:item_name,:start_x,:start_y,:stop_x,:stop_y,:image_path
                    )"""), j)

            # 좌표 삭제
            if template_update_info["del_edit"]:
                # if "del_edit" in template_update_info.keys():
                for k in template_update_info['del_edit']:
                    k['user_id'] = g.user_id
                    app.database.execute(
                        text("""DELETE FROM ocr_template WHERE id=:id AND user_id=:user_id"""), k)

            return "수정성공", 200

    # 템플릿 전체 삭제 - 테스트완료
    @app.route('/template-del', methods=('POST', 'OPTION'))
    @login_required
    def template_del():
        if request.method == 'POST':
            template_del_name = request.json
            template_del_name['user_id'] = g.user_id

            row = app.database.execute(text(
                """SELECT image_path FROM ocr_template WHERE user_id=:user_id AND template_name=:template_name"""), template_del_name).fetchone()
            if os.path.isfile(row['image_path']):
                os.remove(row['image_path'])

            app.database.execute(text(
                """DELETE FROM ocr_template WHERE user_id=:user_id AND template_name=:template_name"""), template_del_name)
            return "삭제성공"

    # 템플릿 ocr - 테스트완료
    @app.route('/template-ocr/<ocr_type>', methods=('POST', 'OPTION'))
    @login_required
    def template_ocr_result(ocr_type):
        if request.method == 'POST':
            template_information = request.json


            if template_information['image'] is None:
                return "not found image",400

            #template_information['image']는 배열

            ocr_type = int(ocr_type)

            f_path1 = app.config['IMAGE_PATH']+'/user_info'
            if not os.path.isdir(f_path1):
                os.mkdir(f_path1)

            f_path2 = f_path1+'/'+g.user_id
            if not os.path.isdir(f_path2):
                os.mkdir(f_path2)

            # ocr_temp => 크롭된 이미지 저장
            f_path = f_path2+'/ocr_temp'
            if not os.path.isdir(f_path):
                os.mkdir(f_path)

            f_crop_image = f_path+'/ocr_crop_temp'
            if not os.path.isdir(f_crop_image):
                os.mkdir(f_crop_image)

            # ocr_image_temp => 크롭할 원본이미지 저장.
            f_crop_before_image = f_path+'/ocr_image_temp'
            if not os.path.isdir(f_crop_before_image):
                os.mkdir(f_crop_before_image)
        
            # image_path = f_path + \
            #     (template_information['image'])[3:7]+"temp_img.png"
            count=0
            list_rength = len(template_information['image'])
            img_num = 1
            return_crop_info = []
            return_result = {}
            for k in template_information['image']:
                count+=1
                image_path = f_crop_before_image + "/"+"temp_img"+str(count)+".png"


                image_decode = base64.b64decode(k)

            # if not os.path.isfile(image_path):
            #     with open(image_path, 'wb') as f:
            #         f.write(image_decode)
                with open(image_path, 'wb') as f:
                    f.write(image_decode)

                img2 = cv2.imread(image_path)
                
            # crop_img_array=[]

                try:
                    for i in template_information['template_info']:
                        img = img2.copy()
                        crop_result = {}
                        x = int(i['start_x'])
                        y = int(i['start_y'])
                        w = int(i['stop_x'])
                        h = int(i['stop_y'])

                        cv2.rectangle(img, (x, y), (w, h), (36, 255, 12), 2)
                        crop_img = img[y:h, x:w]

                        crop_path = f_crop_image+"/crop"+str(img_num)+".png"
                        check = cv2.imwrite(crop_path, crop_img)

                        if check:
                            img = cv2.imread(crop_path)

                            if ocr_type == 1:
                                crop_result["result"] = pytesseract.image_to_string(
                                    img, lang='eng', config='--oem 3 --psm 6')
                            elif ocr_type == 2:
                                crop_result["result"] = pytesseract.image_to_string(
                                    img, lang='kor_new', config='--oem 3 --psm 6')
                            elif ocr_type == 3:
                                crop_result["result"] = pytesseract.image_to_string(
                                    img, lang='eng+kor_new', config='--oem 3 --psm 6')
                            else:
                                return Response(status=404)

                        crop_result["item_name"] = i["item_name"]
                        crop_result["page"] = count

                        with open(crop_path, 'rb') as im:
                            crop_result["image"] = base64.b64encode(
                                im.read()).decode('utf8')

                        # if os.path.isfile(crop_path):
                            # os.remove(crop_path)

                        img_num += 1
                        return_crop_info.append(crop_result)

                    return_result["template_return_info"] = return_crop_info
                except:
                    return 'error',404

            return json.dumps(return_result)

    #템플릿 ocr에서 필드명과 텍스트 결과로 엑셀파일 만들기(xlsx로 만듦 , 컬럼은 필드명으로) - 작업중
    @app.route('/template-ocr-excel',methods=('POST','OPTION'))
    @login_required
    def template_ocr_excel():
        if request.method == 'POST':
            template_result_info = request.json
            print("asdfas",template_result_info)


            #엑셀파일 저장할 위치
            f_path = app.config['IMAGE_PATH']+'/user_info'+'/'+g.user_id+'/ocr_temp/crop_result_file'
            if not os.path.isdir(f_path):
                os.mkdir(f_path)

            field_list = template_result_info["template_result_field_name"]

            excel_dict ={}
            for j in field_list:
                excel_dict[j] = list()


            for i in template_result_info["template_result"]:
                excel_dict[i['field_name']].append(i['result_text'])

            temp_result = pd.DataFrame(excel_dict)
            print(temp_result)


            # with pd.ExcelWriter(f_path+'/template_excel.xlsx', mode='w', engine='openpyxl') as writer:
            with pd.ExcelWriter(f_path+'/'+g.user_id+'_template_excel.xlsx', mode='w', engine='xlsxwriter') as writer:
                temp_result.to_excel(writer, sheet_name="result")    

            return send_file(f_path+'/template_excel.xlsx')

    # 이미지에서 테이블을 검출하는 엔드포인트 - 작업중
    @app.route('/table-find', methods=('POST', 'OPTION'))
    @login_required
    def find_table():
        if request.method == 'POST':
            user_name = g.user_id

            if 'file' not in request.files:
                return 'File is missing', 404


            req = request.files.getlist("file")

            return_json = {}
            img_path = os.getcwd()+'/api_test/imagedir/table_temp/'+user_name

            # 테이블 저장할 폴더 생성
            if not os.path.exists(img_path):
                os.makedirs(img_path+'/img')
                os.mkdir(img_path+'/crops')
                os.mkdir(img_path+'/result')

            # 테이블 저장할 폴더가 있다면
            else:
                if os.listdir(img_path+'/img'):
                    os.system('rm '+img_path+'/img/*')

                if os.listdir(img_path+'/crops'):
                    os.system('rm '+img_path+'/crops/*')

            try:
                # 파일 저장
                for k in req:

                    file_name = secure_filename(k.filename)
                    k.save(img_path+'/img/'+file_name)

                    if os.path.splitext(file_name)[1] == '.pdf':
                        for i,page in enumerate(convert_from_path(img_path+'/img/'+file_name)):
                            temp_name = os.path.splitext(file_name)[0] + str(i) + '.jpg'
                            page.save(img_path + '/img/'+temp_name,'JPEG')
                        os.system('rm '+'"'+img_path+'/img/'+file_name+'"')

                    # 테이블 찾아내는 함수
                tab.find_table(img_path)
            except Exception as ex:
                return Response(status=404)

            # 크롭된 파일을 하나씩 읽어서 base인코딩후 리스트에 담기
            crop_list = list()
            if os.listdir(img_path+'/crops'):
                for i in os.listdir(img_path+'/crops'):
                    with open(img_path+'/crops/'+i, 'rb') as im:
                        crop_list.append(base64.b64encode(
                            im.read()).decode('utf8'))

                return_json['crop_image'] = crop_list

                return json.dumps(return_json), 200
            else:
                return "not found table", 204

    # 검출된 테이블을 엑셀로 변환후 리턴 - POST로 검출한 테이블 사진을 받아서 엑셀 변환 - 작업중
    @app.route('/table-result-download', methods=('GET', 'OPTION'))
    @login_required
    def table_result2():
        if request.method == 'GET':
            try:
                user_name = g.user_id

                img_path = os.getcwd()+'/api_test/imagedir/table_temp/'+user_name

                if os.listdir(img_path+'/result'):
                    os.system('rm '+img_path+'/result/*')

                proc.execute(img_path)
                result_dir = img_path+'/result'
            except:
                return 'error', 500
            return send_file(img_path+'/result/'+os.listdir(result_dir)[0])
            # return "hello"
        else:
            return Response(status=404)

    #인증확인 - 테스트완료
    @app.route('/auth-check', methods=('GET', 'OPTION'))
    @login_required
    def auth_check():
        if request.method == 'GET':
            temp = g.user_id
            return temp  # Response(status=200)filename

    # 전체 ocr - 테스트완료
    @app.route('/normal-all-ocr/<ocr_type>', methods=('GET', 'POST', 'OPTION'))
    def normal_all(ocr_type):
        if request.method == 'POST':
            if 'file' not in request.files:
                return 'File is missing', 404
            #f = request.files["file"]
            return_json = dict()
            temp_list = list()
            ocr_type = int(ocr_type)

            for f in request.files.getlist("file"):
                print(f)

                if f.filename == '':
                    return 'File is missing', 404

                filename = secure_filename(f.filename)
                if not os.path.isdir(app.config['IMAGE_PATH']+'/normal_all_ocr'):
                    os.mkdir(app.config['IMAGE_PATH']+'/normal_all_ocr')

                f.save(app.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)

                if os.path.splitext(app.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)[1] == '.pdf':
                    for i,page in enumerate(convert_from_path(app.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)):
                        
                        temp_name = os.path.splitext(filename)[0] + str(i) + '.jpg'
                        page.save(app.config['IMAGE_PATH']+'/normal_all_ocr/' + temp_name,'JPEG')

                        img = cv2.imread(app.config['IMAGE_PATH']+'/normal_all_ocr/'+temp_name)
                        if ocr_type == 1:
                            temp = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6')
                        elif ocr_type == 2:
                            temp = pytesseract.image_to_string(img, lang='kor_new', config='--oem 3 --psm 6')
                        elif ocr_type == 3:
                            temp = pytesseract.image_to_string(img, lang='eng+kor_new', config='--oem 3 --psm 6')
                        else:
                            return Response(status=404)
                        temp_list.append(temp)
                else:
                    img = cv2.imread(
                        app.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)

                    if ocr_type == 1:
                        temp = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6')
                    elif ocr_type == 2:
                        temp = pytesseract.image_to_string(img, lang='kor_new', config='--oem 3 --psm 6')
                    elif ocr_type == 3:
                        temp = pytesseract.image_to_string(img, lang='eng+kor_new', config='--oem 3 --psm 6')
                    else:
                        return Response(status=404)

                    temp_list.append(temp)

                # if os.path.isfile(os.path.join(app.config['IMAGE_PATH']+'/normal_all_ocr/',filename)):
                # os.remove(os.path.join(app.config['IMAGE_PATH']+'/normal_all_ocr/',filename))
            return_json['text'] = temp_list

            return json.dumps(return_json)
        else:
            return 'invalid method', 404

    return app

    if __name__ == '__main__':

        create_app().run(host='0.0.0.0', port=9009, debug=True)
