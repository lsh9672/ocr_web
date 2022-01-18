from datetime import datetime,timedelta
import jwt,os,base64,json,bcrypt


class UserService:

    def __init__(self,user_dao,config):
        self.user_dao = user_dao
        self.config = config

    #유서 생성 로직
    def create_new_user(self,new_user):

        if len(new_user['user_id']) < 1 or len(new_user['passwd']) < 1 or len(new_user['user_email']) < 1:
            return "length_error"

        #비밀번호에 해시 적용
        new_user['passwd'] = bcrypt.hashpw(
            new_user['passwd'].encode('UTF-8'), bcrypt.gensalt())
        
        new_user_id = self.user_dao.insert_user(new_user)

        return new_user_id

    def sign_in(self,credential):
        user_id = credential['user_id']
        passwd = credential['passwd']

        user_credential = self.user_dao.get_user_id_passwd(user_id)

        if user_credential == "not_id":
            return 'not_id'

        authorized = bcrypt.checkpw(passwd.encode('UTF-8'), user_credential['passwd'].encode('UTF-8'))

        return authorized

    #유저 id 와 비밀번호 가져오기
    def get_user_id_passwd(self,user_id):
        return self.user_dao.get_user_id_passwd(user_id)

    #토큰 발급
    def generate_access_token(self,user_id):
        # 아이디 값을 받아서 템플릿 테이블 조회해서 템플릿 명 전부 가져와서 json으로 만들고 페이로드에 담기
        # exp는 유효기간을 말함(jwt 즉 토큰의 유효기간)
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow()+timedelta(seconds=self.config['JWT_EXP_DELTA_SECOND'])
        }
        token = jwt.encode(
            payload, self.config['JWT_SECRET_KEY'], 'HS256')

        return token

    def template_add_service(self,new_template):

        f_path2 = self.config['IMAGE_PATH']+"/user_info"

        filename = new_template['template_name']
        
        if not os.path.isdir(f_path2):
            os.mkdir(f_path2)

        f_path = self.config['IMAGE_PATH']+"/user_info/"+new_template['user_id']
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

        template_name_result = self.user_dao.template_add_dao(new_template,image_save_path,new_template['user_id'])
        
        #추가된 템플릿 네임 반환 또는 실패했을떄 None
        return template_name_result

    #템플릿 좌표 정보를 받아서 해당 경로의 이미지를 찾아서 반환할 json에 추가
    def template_find_service(self,template_name):

        template_find_dao_result = self.user_dao.template_find_dao(template_name)

        if template_find_dao_result == "not_found_table" or template_find_dao_result is None:

            return template_find_dao_result

        else:
            temp = {}
        
            template_value = [{
                'id': row['id'],
                'item_name': row['item_name'],
                'start_x': row['start_x'],
                'start_y': row['start_y'],
                'stop_x': row['stop_x'],
                'stop_y': row['stop_y']
            } for row in template_find_dao_result]

            img_path = template_find_dao_result[0]['image_path']
            if os.path.isfile(img_path):
                with open(img_path, 'rb') as im:
                    send_image = base64.b64encode(im.read()).decode('utf8')
                return_value = {'template_name': template_name['template_name'],
                                'template_info': template_value, 'image': send_image, 'image_path': img_path}
                return json.dumps(return_value)
            else:
                return "not_found_file"

    #템플릿 전체 이름 조회 한 결과를 json형식으로 수정
    def template_all_name_service(self,user_id):

        template_all_result = self.user_dao.template_all_name_dao(user_id)

        if template_all_result is None:
            return None

        else:
            temp = set([row['template_name'] for row in template_all_result])

            result_all = {}
            result_all["template_name_list"] = list(temp)

            return json.dumps(result_all)

    #템플릿 정보 업데이트 서비스 로직(여기서는 persistence쪽으로 넘기기만 함)
    def template_update_service(self,template_update_info,user_id):
        
        update_result_dao_result = self.user_dao.template_update_dao(template_update_info,user_id)

        #False or True return
        return update_result_dao_result

    #템플릿 정보 삭제 서비스 로직(persistence로 넘기기만 함.)
    def template_del_service(self,template_del_name):

        template_del_dao_result = self.user_dao.template_del_dao(template_del_name)

        return template_del_dao_result
    

