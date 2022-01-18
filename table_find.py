import cv2
import yolov5
import os

def find_table(dirpath):
    print('test',dirpath)
    print('hello')
    model = yolov5.load(os.getcwd()+'/api_test/best.pt')

    file_list = os.listdir(dirpath+'/img')
    print(file_list)
    for file_name in file_list:

        img = cv2.imread(dirpath+'/img/'+file_name)

        img_ori = img.copy()
        img_count = 0

        results = model(img)

        predictions = results.pred[0]

        predictions = predictions.cpu().numpy()

        #boxes = predictions[:, :4]  # x1, x2, y1, y2
        #scores = predictions[:, 4]
        #categories = predictions[:, 5]

        for box in predictions:
            if box[4] > 0.8:
                img_result = cv2.rectangle(img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 120), 2)
                img_count += 1
                img_crop= img_ori[int(box[1]):int(box[3])+3,int(box[0]):int(box[2])+3]
                save_img = cv2.imwrite(dirpath+'/crops/'+file_name.split('.')[0]+str(img_count)+'.jpg',img_crop)