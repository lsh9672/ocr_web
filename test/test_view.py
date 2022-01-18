from re import M
from api_test.app import create_app
from sqlalchemy import create_engine,or_,text
import config
import pytest
import json
import bcrypt
# from unittest import mock
import io,os,shutil
import base64

database = create_engine(config.test_config['DB_URL'], encoding='utf-8', max_overflow=0)

@pytest.fixture
def api():

    app = create_app(config.test_config)
    app.config['TEST'] = True
    api=app.test_client()


    return api

#테스트 코드 실행전에 필요한 셋팅을 하는 함수. 각 테스트를 하기전에 먼저 실행되는 함수이다.
def setup_function():
    #테스트를 위한 유저를 생성함.
    hashed_password = bcrypt.hashpw(b"test passwd",bcrypt.gensalt())

    new_user={
        "user_id":"test07",
        "user_eamil":"test07@gmail.com",
        "passwd":hashed_password
    }

    new_user_id = database.execute(text(
                        """INSERT INTO users(user_id,user_email,passwd) VALUES(:user_id,:user_email,:passwd)"""), new_user)
    #테스트를 위한 이미지 파일 저장 디렉터리 생성
    if not os.path.exists(os.getcwd()+'/api_test/test_imagedir'):
        os.makedirs(os.getcwd()+'/api_test/test_imagedir/table_temp')
        shutil.copy(os.getcwd()+'/api_test/test_img.png',os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img.png')

    #템플릿 정보 저장
    i = dict()
    i["template_info"] = {"item_name":"test_name2","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
    i['user_id'] = new_user['user_id']
    i['template_name'] = "test_name"
    i['image_path'] = os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img.png'

    new_template_name = database.execute(text("""
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

#테스트가 하나 끝나면 테스트 중에 발생한 데이터를 제거(테스트는 다른 테스트에 종속되면 되면 안됨)
def teardown_function():

    #테이블 삭제를 위해 외래키를 잠시 끔
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE TABLE users"))
    database.execute(text("TRUNCATE TABLE ocr_template"))

    #다시 외래키를 킴
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))
    # database.execute(text("ALTER TABLE users AUTO_INCREMENT=1"))
    if os.path.exists(os.getcwd()+'/api_test/test_imagedir'):
        shutil.rmtree(os.getcwd()+'/api_test/test_imagedir')

#템플릿 이름 가져오기(넣고 잘 들어갔는지 확인을 위해서)
def get_template_name(user_id):
    temp = {"user_id":user_id}
    rows = database.execute(text("""
    SELECT
    template_name
    FROM ocr_template
    WHERE user_id= :user_id
    """), temp).fetchall()

    return rows

#디비에서 템플릿 정보 가져오기
def get_template(user_id:str,template_name:str):
    temp = {"user_id":user_id,"template_name":template_name}
    rows = database.execute(text("""
    SELECT
    item_name
    FROM ocr_template
    WHERE user_id= :user_id AND template_name=:template_name
    """), temp).fetchall()
    return rows


#핑테스트
def test_ping(api):
    resp = api.get('/ping')

    #바이트데이터로 오기 때문에 바이트로 변환해서 비교함.
    assert b'pong' in resp.data


def test_sign_in(api):
    
    resp = api.post('/sign_in', data = json.dumps({'user_id':'test07',"passwd":"test passwd"}), content_type='application/json')

    assert b'access_token' in resp.data

#인증토큰 없이 접속했을때 400번때 에러가 나는지 확인
def test_unauthorized(api):

    #아래의 post 값들은 인증에서 걸러질것이므로 아무값이나 넣어서 보냄(형식은 맞게 해서)
    template_add_data = {
        "template_name":"test_name02",
        "template_info":[
            {"item_name":"크롭한 좌표의 이름","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
            ],
        "image":"aGVsbG8gd29ybGQ="
    }
    template_value_data = {
        "template_name":"test_name"
    }
    template_all_name_data = {
        "template_name_info":[
            {"template_name":"저장된 템플릿 이름"}
            ]
    }
    template_update_data = {
        "template_name":"test_name",
        "edit":[],
        "add_edit":[],
        "del_edit":[],
        "image_path":"/test"
    }
    template_del_data ={
        "template_name":"삭제할 템플릿 명"
    }
    template_ocr_data = {
        "template_info":[
            {"item_name":"좌표의 이름","start_x":1,"start_y":2,"stop_x":3,"stop_y":4}
            ],
        "image":"aGVsbG8gd29ybGQ="
    }

    #access token 업이 접속하면 401이 뜨는 것을 확인
    resp = api.post('/template-add',json.dumps(template_add_data),content_type='application/json')
    assert resp.status_code == 401

    resp = api.post('/template-value',json.dumps(template_value_data),content_type='application/json')
    assert resp.status_code == 401

    resp = api.post('/template-all-name',json.dumps(template_all_name_data),content_type='application/json')
    assert resp.status_code == 401

    resp = api.post('/templat-update',json.dumps(template_update_data),content_type='application/json')
    assert resp.status_code == 401

    resp = api.post('/template-del',json.dumps(template_del_data),content_type='application/json')
    assert resp.status_code == 401

    resp = api.post('/template-ocr/1',json.dumps(template_ocr_data),content_type='application/json')
    assert resp.status_code == 401

# presentation 계층의 /template-add 엔드포인트 테스트
def test_template_add(api):
    #테스트용 이미지 base6로 인코딩
    with open(os.getcwd()+'/api_test/test_img.png','rb') as f:
        temp_img = base64.b64encode(f.read()).decode('utf-8')
    

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    request_data = {
        "template_name":"test_name09",
        "template":[
            {"item_name":"좌표의 이름","start_x":30,"start_y":60,"stop_x":80,"stop_y":4}
        ],
        "image":temp_img
    }

    resp = api.post('/template-add',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200

    assert resp.data.decode('utf-8') == "test_name09"

    assert {"template_name":"test_name09"} in get_template_name("test07")

# presentation 계층의 /template-value 엔드포인트 테스트
def test_template_value(api):

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    
    request_data = {
        "template_name":"test_name"
        }

    resp = api.post('/template-value',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200

    #값을 한개만 넣어 뒀기 때문에 리스트 길이가 1이 나와야 됨.
    temp = json.loads(resp.data.decode('utf-8'))
    assert len(temp["template_info"]) == 1

#presentation 계층에서 /template-all-name 엔드포인트 테스트
def test_template_all_name(api):

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    #api에 요청
    resp = api.get('/template-all-name',headers = {'Authorization': access_token})

    assert resp.status_code == 200


    temp = json.loads(resp.data.decode('utf-8'))
    assert temp[0]["template_name"] == "test_name"

#presentation 계층에서 /template-update 엔드포인트 테스트
def test_template_update(api):

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    #수정중에서 기존데이터에서 추가가 되었을때 테스트
    request_data = {
        "template_name":"test_name",
        "edit":[],
        "add_edit":[{"item_name":"test_name3","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}],
        "del_edit":[],
        "image_path":os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img.png'
    }
    resp = api.post('/template-update',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200
    assert resp.data.decode("utf-8") == "update success"

    #조회한 템플릿 item_name안에  추가한 정보가 있는지 확인
    temp = get_template("test07","test_name")
    assert {"item_name":"test_name3"} in temp

#presentation 계층에서 /template-del 엔드포인트 테스트  
def test_template_del(api):

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    request_data = {
        "template_name":"test_name"
    }
    resp = api.post('/template-del',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200
    assert resp.data.decode("utf-8") == "delete success"

    #데이터가 삭제되었는지 확인 - 1개 있는 데이터를 삭제했기 때문에 None이 나와야 됨
    assert get_template_name("test07") is None

#presentation계층에서 /template-ocr/<ocr_type>
def test_template_ocr_result(api):
    #테스트용 이미지 base64로 인코딩
    with open(os.getcwd()+'/api_test/test_img.png','rb') as f:
        temp_img = base64.b64encode(f.read()).decode('utf-8')

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    #ocr_type이 잘못되었을때 테스트(4는 없는 값)
    request_data = {
        "template_info":[
            {"item_name":"test_name3","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
        ],
        "image":temp_img
    }

    resp = api.post('/template-ocr/4',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 404
    assert resp.data.decode("utf-8") == "type error"
    
    #ocr_type제대로 되었을떄
    request_data = {
        "template_info":[
            {"item_name":"test_name3","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
        ],
        "image":temp_img
    }
    resp = api.post('/template-ocr/1',json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200
    
    #위의 테스트 데이터로 ocr을 하면 결과가 나옴(실제로 돌려봤을때 결과가 나오는 이미지임)
    temp = json.loads(resp.data.decode("utf-8"))
    assert temp != None

#presentation 계층의 template_ocr_excel 엔드포인트 테스트
def test_template_ocr_excel(api):

    #crop된 결과 이미지로 사용
    with open(os.getcwd()+'/api_test/test_img.png','rb') as f:
        temp_img = base64.b64encode(f.read()).decode('utf-8')

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    #crop된 이미지와 필드명으로 엑셀 파일 생성되는지 확인(상태코드만 확인하기)
    request_data = {
        "template_result":[
            {
                "result_text":temp_img,
                "field_name":"name1"
            },
            {
                "result_text":temp_img,
                "field_name":"name2"
            }
        ],
        "template_result_field_name":["name1","name2"]
    }
    resp = api.post('/template-ocr-excel',data = json.dumps(request_data),content_type='application/json',headers = {'Authorization': access_token})
    assert resp.status_code == 200

#presentation에서 /table-find 엔드포인트 테스트 - 테스트에서는 임의로 만든 바이트 데이터로 테스트하기 때문에 표가 추출되는 것은 테스트 불가
def test_table_find(api): 
    #이미지를 폼데이터로 보냄

    #인증이 필요한 엔드포인트는 로그인을 해서 토큰을 발급받음
    resp = api.post('/sign-in', data = json.dumps({"user_id":"test07","password":"test passwd"}),content_type = 'application/json')
    resp_json = json.loads(resp.data.decode("utf-8"))
    access_token = resp_json["access_token"]

    #io.ByteSIO 클래스를 이용해서 테스트 byte데이터를 전송하는 것처럼 전송
    request_data = {'file':(io.BytesIO(b"test_image"),"test_img2.png")}
    resp = api.post('/table-find',data = request_data,content_type="multipart/form-data",headers = {'Authorization': access_token})

    #위에서 만든 데이터로는 표가 검출되지 않음
    assert resp.status_code == 204


def test_normall_all(api):

    request_data = {'file':(io.BytesIO(b"test_image"),"test_img2.png")}

    #없는 타입을 요청했을떄 테스트
    resp = api.post('/normal-all-ocr/4',data = request_data,content_type="multipart/form-data")
    assert resp.status_code == 404
    assert resp.data.decode("utf-8") == "type error"

    #결과는 알수 없지만 데이터가 있기 때문에 로직은 성공적으로 동작함.
    resp = api.post('/normal-all-ocr/1',data = request_data,content_type="multipart/form-data")
    assert resp.status_code == 200


