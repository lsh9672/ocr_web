import bcrypt
import pytest,os
import config,shutil
from api_test.models import UserDao
from sqlalchemy import create_engine,or_,text
import base64

database = create_engine(
        config.test_config['DB_URL'], encoding='utf-8', max_overflow=0)

@pytest.fixture
def user_dao():
    return UserDao(database)


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
    
    i = dict()
    i["template_info"] = {"item_name":"test_name2","start_x":30,"start_y":60,"stop_x":60,"stop_y":30}
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


#디비에서 유저 정보 조회 - insert테스트 할때사용
def get_user(user_id):
    row = database.execute(text("""SELECT user_id,user_email FROM users WHERE user_id = :user_id"""), {'user_id': user_id}).fetchone()

    return {"user_id":row["user_id"],"user_email":row["user_email"]}

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

#템플릿 추가(del 함수 테스트를 위해서)
def add_template(user_id:str):
    #테스트 이미지 저장
    shutil.copy(os.getcwd()+'/api_test/test_img.png',os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img4.png')

    temp ={
        "user_id":user_id,
        "template_name":"test_name03",
        "item_name":"test04",
        "start_x":30,
        "start_y":60,
        "stop_x":80,
        "stop_y":30,
        "image_path":str(os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img4.png')
        }

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
        )"""), temp).lastrowid
    
    return new_template_name

#삭제하고 나서 확인을 위해
def get_template_name(user_id):
    temp = {"user_id":user_id}
    rows = database.execute(text("""
    SELECT
    template_name
    FROM ocr_template
    WHERE user_id= :user_id
    """), temp).fetchall()

    return rows


#user_dao의 insert_user 테스트
def test_insert_user(user_dao):
    new_user={
        "user_id":"test08",
        "user_eamil":"test08@gmail.com",
        "passwd":"test passwd"
    }
    
    insert_user_result = user_dao.insert_user(new_user)
    assert insert_user_result == "success"

    assert get_user(new_user["user_id"]) == {"user_id":"test08","user_email":"test08@gmail.com"}
    
#user_dao의  get_user_id_passwd 함수 테스트
def test_get_user_id_passwd(user_dao):
    user_id = "test07",

    user_credential = user_dao.get_user_id_passwd("test08")

    assert bcrypt.checkpw('test passwd'.encode('UTF-8'),user_credential['hashed_password'].encode('UTF-8'))

#user_dao의 template_add_dao 함수 테스트
def test_template_add_dao(user_dao):

    #테스트 이미지 저장
    shutil.copy(os.getcwd()+'/api_test/test_img.png',os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img2.png')
    #테스트용 이미지 base64로 인코딩
    with open(os.getcwd()+'/api_test/test_img.png','rb') as f:
        temp_img = base64.b64encode(f.read()).decode('utf-8')

    temp ={
        "template_name":"test_name02",
        "template_info":[
            {"item_name":"test03","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
            ],
        "image":temp_img
        }

    template_add_result = user_dao.template_add_dao(temp,os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img2.png',"test07")

    assert template_add_result == "test_name02"

#user_dao의 template_find_dao함수 테스트
def test_template_find_dao(user_dao):
    result = user_dao.template_find_dao("test_name")

    assert result == {
        "id":1,
        "item_name":"test_name2",
        "start_x":30,"start_y":60,"stop_x":80,"stop_y":30,
        "image_path":str(os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img.png')
        }

#user_dao의 template_all_name_dao 함수 테스트
def test_template_all_name_dao(user_dao):
    result = user_dao.template_all_name_dao("test07")

    assert result == [{"template_name":"test_name"}]

#user_dao의 template_update_dao 함수 테스트(기존데이터를 그대로 두고 새로 추가하는 것만 테스트)
def test_template_update_dao(user_dao):
    update_json = {
        "template_name":"test_name",
        "add_edit":[{"item_name":"test_name3","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}
        ],
        "edit":[],
        "del_edit":[],
        "image_path":str(os.getcwd()+'/api_test/test_imagedir/user_info/test07/test_img.png')
        }
    result = user_dao.template_update_dao(update_json,"test07")

    assert result == True

    #값이 업데이트 되었는지 확인
    result = get_template("test07","test_name")
    assert {"item_name":"test_name3"} in result

#템플릿 삭제
def test_template_del_dao(user_dao):
    #삭제할 데이터 넣기
    add_template("test07")
    template_del_name = {"user_id":"test07","template_name":"test_name03"}

    result = user_dao.template_del_dao(template_del_name)

    assert result == True

    result = get_template_name("test07")

    assert result not in {"template_name":"test_name03"}




