import bcrypt
import pytest
import config
from api_test.service import OcrService,UserService
from api_test.models import UserDao
from sqlalchemy import create_engine,or_,text
import jwt,os,shutil
import base64

database = create_engine(
        config.test_config['DB_URL'], encoding='utf-8', max_overflow=0)

@pytest.fixture
def user_service():

    return UserService(UserDao(database),config.test_config)

@pytest.fixture
def ocr_service():
    return OcrService(config.test_config)


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

#유저 정보 가져오기
def get_user_id(user_id):
    row = database.execute(text("""SELECT passwd FROM users WHERE user_id = :user_id"""), {'user_id': user_id}).fetchone()
    return row["user_id"]

'''비즈니스 레이어 테스트(service디렉토리)'''
#유저 생성 - 완료
def test_create_new_user(user_service):

    new_user = {
        'user_id':"test08",
        'passwd':"test passwd",
        'user_email':"test08@gmail.com"
    }

    new_user_id = user_service.create_new_user(new_user)


    assert "test08" == get_user_id(new_user["user_id"])

#로그인 비즈니스 레이어 테스트 - 완료
def test_sign_in(user_service):

    credential = {
        'user_id':"test08",
        'passwd':"test passwd"
    }
    assert user_service.sign_in(credential) != "not_id" 
    assert user_service.sign_in(credential) != None

#유저 아이디 비밀번호 가져오기 테스트 - 완료
def test_get_id_passwd(user_service):

    user_id = "test07"

    assert user_service.get_user_id_passwd(user_id)["user_id"] == "test07"

#
def test_generate_access_token(user_service):

    user_id = "test07"
    token = user_service.generate_access_token(user_id)
    #토큰 받아서 디코딩
    payload = jwt.decode(token,config.JWT_SECRET_KEY,'HS256')

    assert payload["user_id"] == "test07"

#business 계층의 template_add_service함수 테스트
def test_template_add_service(user_service):
    #테스트용 이미지 base64로 인코딩
    with open(os.getcwd()+'/api_test/test_img.png','rb') as f:
        temp_img = base64.b64encode(f.read()).decode('utf-8')
    
    new_template = {
        "user_id":"test07",
        "template_name":"test_name09",
        "template_info":[{"item_name":"test_item_name09","start_x":30,"start_y":60,"stop_x":80,"stop_y":30}],
        "image":temp_img
    }

    #로직이 제대로 실행되는지 확인(실패했으면 None)
    result = user_service.template_add_service(new_template)
    assert result == "test_name09"      

    #저장이 되었는지 확인
    result = get_template_name("test07")
    assert {"template_name":"test_name_09"} in result

#business 계층의 template_find_service 함수 테스트
def test_template_find_service(user_service):

    template_name = {
        "user_id":"test07",
        "template_name":"test_name"
    }
    
    result = user_service.template_find_service(template_name)
    assert result["template_name"] == "test_name"

#business 계층의 template_all_nae_service 함수 테스트
def test_template_all_name_service(user_service):

    user_id = "test07"
    result = user_service.template_all_name_service(user_id)

    #조회한 정보안에 있어야되는 이름이 있는지 확인
    assert "test_name" in result["template_name_list"]


'''아래 두개는 단순히 dao쪽에 바로 넘기기만 하기 때문에 dao쪽의 함수가 테스트를 통과하게 되면
아래의 두 함수는 별도의 로직이 없기 때문에 잘 동작하게 됨.'''
# def test_template_update_service(user_service):
    
    
# def template_del_service(user_service):
    


