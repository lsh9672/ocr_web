import cv2,jwt,os,base64,json,pytesseract,bcrypt
import pandas as pd
from werkzeug.utils import secure_filename
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from pdf2image import convert_from_path
import api_test.table_find as tab
import api_test.table_processing as proc
    
class OcrService:

    def __init__(self,config):
        self.config = config
    
    #템플릿 ocr 서비스 로직
    def template_ocr_service(self,template_information:dict,ocr_type:int,user_id:str) -> dict:
        ocr_type = int(ocr_type)

        f_path1 = self.config['IMAGE_PATH']+'/user_info'
        if not os.path.isdir(f_path1):
            os.mkdir(f_path1)

        f_path2 = f_path1+'/'+user_id
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
                            return "type_error"

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
                return None

        return return_result

    #템플릿 ocr결과를 엑셀로 저장하고 경로를 반환하는 서비스 로직
    def template_result_info_service(self,template_result_info:dict,user_id:str)->str:
        try:
            #엑셀파일 저장할 위치
            f_path = self.config['IMAGE_PATH']+'/user_info'+'/'+user_id+'/ocr_temp/crop_result_file'
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
            with pd.ExcelWriter(f_path+'/'+user_id+'_template_excel.xlsx', mode='w', engine='xlsxwriter') as writer:
                temp_result.to_excel(writer, sheet_name="result")

        except Exception as ex:
            return None

        return f_path+'/'+user_id+'_template_excel.xlsx'

    #이미지에서 테이블을 검출하는 서비스 로직, 검출해서 json에 담아서 보냄
    def table_find_service(user_id:str,req:list) -> dict:
        return_json = {}
        img_path = os.getcwd()+'/api_test/imagedir/table_temp/'+user_id

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
            return None

        # 크롭된 파일을 하나씩 읽어서 base인코딩후 리스트에 담기
        crop_list = list()
        if os.listdir(img_path+'/crops'):
            for i in os.listdir(img_path+'/crops'):
                with open(img_path+'/crops/'+i, 'rb') as im:
                    crop_list.append(base64.b64encode(
                        im.read()).decode('utf8'))

            return_json['crop_image'] = crop_list

            return return_json
        else:
            return "not found table"

    #검출된 테이플(표)를 엑셀로 변환해서 경로를 반환하는 서비스 로직
    def table_result_download_service(self,user_id):
        try:
            
            img_path = os.getcwd()+'/api_test/imagedir/table_temp/'+user_id

            if os.listdir(img_path+'/result'):
                os.system('rm '+img_path+'/result/*')

            proc.execute(img_path)
            result_dir = img_path+'/result'
        except:
            return None
        return str(img_path+'/result/'+os.listdir(result_dir)[0])

    #전체 ocr(이미지에 있는 글자를 인식해서 그대로 출력)을 처리하는 서비스 로직
    def normal_all_ocr_service(self,req:list,ocr_type:int) -> dict:
        
        return_json = dict()
        temp_list = list()
        try:
            for f in req:
                print(f)

                if f.filename == '':
                    return 'File is missing', 404

                filename = secure_filename(f.filename)
                if not os.path.isdir(self.config['IMAGE_PATH']+'/normal_all_ocr'):
                    os.mkdir(self.config['IMAGE_PATH']+'/normal_all_ocr')

                f.save(self.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)

                if os.path.splitext(self.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)[1] == '.pdf':
                    for i,page in enumerate(convert_from_path(self.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)):
                        
                        temp_name = os.path.splitext(filename)[0] + str(i) + '.jpg'
                        page.save(self.config['IMAGE_PATH']+'/normal_all_ocr/' + temp_name,'JPEG')

                        img = cv2.imread(self.config['IMAGE_PATH']+'/normal_all_ocr/'+temp_name)
                        if ocr_type == 1:
                            temp = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6')
                        elif ocr_type == 2:
                            temp = pytesseract.image_to_string(img, lang='kor_new', config='--oem 3 --psm 6')
                        elif ocr_type == 3:
                            temp = pytesseract.image_to_string(img, lang='eng+kor_new', config='--oem 3 --psm 6')
                        else:
                            return "type_error"
                        temp_list.append(temp)
                else:
                    img = cv2.imread(
                        self.config['IMAGE_PATH']+'/normal_all_ocr/'+filename)

                    if ocr_type == 1:
                        temp = pytesseract.image_to_string(img, lang='eng', config='--oem 3 --psm 6')
                    elif ocr_type == 2:
                        temp = pytesseract.image_to_string(img, lang='kor_new', config='--oem 3 --psm 6')
                    elif ocr_type == 3:
                        temp = pytesseract.image_to_string(img, lang='eng+kor_new', config='--oem 3 --psm 6')
                    else:
                        return "type_error"

                    temp_list.append(temp)

                # if os.path.isfile(os.path.join(app.config['IMAGE_PATH']+'/normal_all_ocr/',filename)):
                # os.remove(os.path.join(app.config['IMAGE_PATH']+'/normal_all_ocr/',filename))
            return_json['text'] = temp_list
        
        except Exception as ex:
            return None

        return return_json