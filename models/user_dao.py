from sqlalchemy import create_engine, text
import os


#유저 관련 디비
class UserDao:

    def __init__(self,database):
        self.db = database

    
    #디비에 회원 정보 넣기 - 완료
    def insert_user(self,new_user):
        try:
            new_user_id = self.db.execute(text(
                        """INSERT INTO users(user_id,user_email,passwd) VALUES(:user_id,:user_email,:passwd)"""), new_user).lastrowid()
        except Exception as ex:
            return None

        return "success" 

    #디비에 저장된 유저 아이디와 암호화된 비밀번호 반환 - 완료
    def get_user_id_passwd(self,user_id):
        try:
            row = self.db.execute(text("""SELECT passwd FROM users WHERE user_id = :user_id"""), {'user_id': user_id}).fetchone()
            
            if row is None:
                return 'not_id'
            else:
                return_result = {"user_id":user_id,"hashed_password":row['passwd']}
            return return_result

        except Exception as ex:
            return None

    #템플릿을 디비에 추가하고 추가한 템플릿 이름을 반환 - 완료
    def template_add_dao(self,new_template,image_save_path,user_id):
        try:
            for i in new_template['template_info']:
                i['user_id'] = user_id
                i['template_name'] = new_template['template_name']
                i['image_path'] = image_save_path

                new_template_name = self.db.execute(text("""
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

            row = self.db.execute(text("""SELECT template_name FROM ocr_template WHERE id=:req_id"""), {'req_id': new_template_name}).fetchone()
        
        except Exception as ex:
            return None

        return row['template_name']

    
    #템플릿 이름으로 좌표 조회
    def template_find_dao(self,template_name):
        try:
            rows = self.db.execute(text("""
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

            return rows

        except:
            return "not_found_table"

    #해당 유저의 모든 템플릿 네임
    def template_all_name_dao(self,user_id):
        try:
            rows = self.db.execute(text("""
            SELECT
            template_name
            FROM ocr_template
            WHERE user_id= :user_id
            """), {"user_id": user_id}).fetchall()

            if rows is None:
                return None

            return rows

        except Exception as ex:
            return None

    #템플릿 정보 디비에서 업데이트 하기 - 완료
    def template_update_dao(self,template_update_info,user_id):
        try:
            # 기존것 수정
            if template_update_info["edit"]:
                # if "edit" in template_update_info.keys():
                for i in template_update_info['edit']:
                    i['user_id'] = user_id
                    i['template_name'] = template_update_info['template_name']

                    i['start_x'] = int(i['start_x'])
                    i['start_y'] = int(i['start_y'])
                    i['stop_x'] = int(i['stop_x'])
                    i['stop_y'] = int(i['stop_y'])

                    self.db.execute(text("""
                    UPDATE ocr_template 
                    SET template_name=:template_name,item_name=:item_name,start_x=:start_x,start_y=:start_y,stop_x=:stop_x,stop_y=:stop_y 
                    WHERE id=:id AND user_id=:user_id"""), i)

            # 새로운 좌표 추가
            if template_update_info["add_edit"]:
                # if "add_edit" in template_update_info.keys():
                for j in template_update_info['add_edit']:
                    j['user_id'] = user_id
                    j['template_name'] = template_update_info['template_name']
                    j['image_path'] = template_update_info['image_path']

                    j['start_x'] = int(j['start_x'])
                    j['start_y'] = int(j['start_y'])
                    j['stop_x'] = int(j['stop_x'])
                    j['stop_y'] = int(j['stop_y'])

                    self.db.execute(text("""
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
                    k['user_id'] = user_id
                    self.db.execute(
                        text("""DELETE FROM ocr_template WHERE id=:id AND user_id=:user_id"""), k)
            
            return True

        except Exception as ex:
            return False

    #디비에서 템플릿 전체 삭제(좌표값 전부 삭제됨)
    def template_del_dao(self,template_del_name):
        try:
            row = self.db.execute(text(
                """SELECT image_path FROM ocr_template WHERE user_id=:user_id AND template_name=:template_name"""), template_del_name).fetchone()
            if os.path.isfile(row['image_path']):
                os.remove(row['image_path'])

            self.db.execute(text(
                """DELETE FROM ocr_template WHERE user_id=:user_id AND template_name=:template_name"""), template_del_name)
            return True

        except Exception as ex:
            return False



