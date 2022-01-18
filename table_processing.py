import pytesseract
import cv2
import numpy as np
import pandas as pd
import os
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import openpyxl


def sort_contours(cnts, method="left-to-right"):
    # initialize the reverse flag and sort index
    reverse = False
    i = 0
    # handle if we need to sort in reverse
    if method == "right-to-left" or method == "bottom-to-top":
        reverse = True
    # handle if we are sorting against the y-coordinate rather than
    # the x-coordinate of the bounding box
    if method == "top-to-bottom" or method == "bottom-to-top":
        i = 1
    # construct the list of bounding boxes and sort them from top to
    # bottom
    boundingBoxes = [cv2.boundingRect(c) for c in cnts]
    (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
    key=lambda b:b[1][i], reverse=reverse))
    # return the list of sorted contours and bounding boxes
    return (cnts, boundingBoxes)

def execute(filedir):
    #crops 디렉토리를 받아서 하위에 있는 파일들을 탐색
    sheet_num = 1
    for k in os.listdir(filedir + '/crops'):

        filename = filedir + '/crops/' + k

        img = cv2.imread(filename, 0)
        img2 = img.copy()
        img_ori = img.copy()
        heights, widths = img.shape

        # 이미지에서 글자 삭제하는 과정
        # boxes = pytesseract.image_to_boxes(img)

        # for b in boxes.splitlines():
        #     b = b.split(' ')
        #     if b[0] !='~' and b[0]!='|':
        #         x_s = int(int(b[1]) + 3)
        #         y_s = int((heights - int(b[2])) - 3)
        #         x_e = int(int(b[3]) - 3)
        #         y_e = int((heights - int(b[4])) + 3)

        #         img = cv2.rectangle(img, (x_s, y_s), (x_e, y_e),
        #                             (255, 255, 255), -1)


        thresh, img_bin = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        img_bin = 255 - img_bin

        kernel_len = np.array(img).shape[1] // 100

        ver_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_len))

        hor_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))


        image_1 = cv2.erode(img_bin, ver_kernel, iterations=2)
        vertical_lines = cv2.dilate(image_1, ver_kernel, iterations=2)

        image_2 = cv2.erode(img_bin, hor_kernel, iterations=2)
        horizontal_lines = cv2.dilate(image_2, hor_kernel, iterations=2)

        img_vh = cv2.addWeighted(vertical_lines, 0.5, horizontal_lines, 0.5, 0.0)
        img_vh = cv2.erode(~img_vh, kernel, iterations=2)

        thresh, img_vh = cv2.threshold(img_vh, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)


        bitxor = cv2.bitwise_xor(img2, img_vh)
        # bitnot = cv2.bitwise_not(bitxor)

        contours, hierarchy = cv2.findContours(img_vh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        contours, boundingBoxes = sort_contours(contours, method="top-to-bottom")

        heights = [boundingBoxes[i][3] for i in range(len(boundingBoxes))]

        mean = np.mean(heights)

        box = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if (w * h > 1000 and w < int(widths*9/10)):

                image = cv2.rectangle(img2, (x, y), (x + w, y + h), (0, 255, 0), 2)

                box.append([x, y, w, h])

        row = []
        column = []

        j = 0
        # 박스 행,열 정렬
        for i in range(len(box)):
            if (i == 0):
                column.append(box[i])
                previous = box[i]
            else:
                if (box[i][1] <= previous[1] + mean / 4):
                    column.append(box[i])
                    previous = box[i]
                    if (i == len(box) - 1):
                        row.append(column)
                else:
                    row.append(column)
                    column = []
                    previous = box[i]
                    column.append(box[i])

        # 최대 셀 수 계
        countcol = 0
        for i in range(len(row)):
            countcol = len(row[i])
            if countcol > countcol:
                countcol = countcol
        # 각 셀 중앙값 검색
        center = [int(row[i][j][0] + row[i][j][2] / 2) for j in range(len(row[i])) if row[0]]
        center = np.array(center)
        center.sort()

        finalboxes = []
        for i in range(len(row)):
            lis = []
            for k in range(countcol):
                lis.append([])
            for j in range(len(row[i])):
                diff = abs(center - (row[i][j][0] + row[i][j][2] / 4))
                minimum = min(diff)
                indexing = list(diff).index(minimum)
                lis[indexing].append(row[i][j])
            finalboxes.append(lis)

        # from every single image-based cell/box the strings are extracted via pytesseract and stored in a list
        outer = []
        for i in range(len(finalboxes)):
            for j in range(len(finalboxes[i])):
                inner = ''
                if (len(finalboxes[i][j]) == 0):
                    outer.append(' ')
                else:
                    for k in range(len(finalboxes[i][j])):
                        y, x, w, h = finalboxes[i][j][k][0], finalboxes[i][j][k][1], finalboxes[i][j][k][2], \
                                    finalboxes[i][j][k][3]
                        finalimg = img_ori[x:x + h, y:y + w]
                        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
                        border = cv2.copyMakeBorder(finalimg, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[255, 255])
                        resizing = cv2.resize(border, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                        dilation = cv2.dilate(resizing, kernel, iterations=1)
                        erosion = cv2.erode(dilation, kernel, iterations=1)


                        out = pytesseract.image_to_string(erosion, lang='eng', config='--psm 6')

                        if (len(out) == 0):
                            out = pytesseract.image_to_string(erosion, lang='eng+kor_new', config='--psm 6')
                        inner = inner + " " + out

                    inner= ILLEGAL_CHARACTERS_RE.sub(r'',inner)

                    outer.append(inner)

        # ocr 결과 정리
        arr = np.array(outer)
        dataframe = pd.DataFrame(arr.reshape(len(row), countcol))
        data = dataframe.style.set_properties(align="left")

        #data.to_excel(filedir+"/result/result_excel.xlsx")


        # 저장할 파일명 지정 - 수정 필요(경로명)
        if os.path.exists(filedir + "/result/result_excel.xlsx"):
            with pd.ExcelWriter(filedir + "/result/result_excel.xlsx", mode='a', engine='openpyxl') as writer:
                data.to_excel(writer, sheet_name="result_" + str(sheet_num))
        else:
            with pd.ExcelWriter(filedir + "/result/result_excel.xlsx", mode='w', engine='openpyxl') as writer:
                data.to_excel(writer, sheet_name="result_" + str(sheet_num))

        sheet_num += 1

        
    

