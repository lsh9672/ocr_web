# 캡스톤 디자인 ocr기술을 제공하는 웹 서비스(2021.03~2021.11)

api 코드를 저장하는 저장소

프론트부분의 코드는 다른 저장소에 있음

## 개발환경

- os : ubuntu 20.04.3
- IDE : vscode
- DB : mysql
- test tool : pytest(unit test)
- framwork : flask(python)
- wsgi : gunicorn

## 구현한 기능(rest api)

- 회원가입, 로그인 기능(jwt를 이용하여 인증 구현)

- 이미지 전체를 ocr 하는 기능구현(tesseract에 추가로 학습해서 만든 모델 사용)

- 이미지에서 표만 인식해서 추출하는 기능구현(yolo v5로 직접 학습한 모델 사용)

- 추출된 표 이미지에서 각 셀을 인식후 ocr 하여 엑셀에 넣고 반환해주는 기능구현

- 이미지에서 원하는 부분만 추출해서 ocr할수 있는 템플릿 기능구현

  1. 원하는 부분의 좌표(템플릿)를 저장해둘 수 있는 기능 구현

  2. 저장해둔 템플릿 이름을 볼 수 있도록 전체 이름을 조회하는 기능 구현

  3. 특정 템플릿의 좌표를 볼 수 있도록 조회하는 기능 구현

  4. 템플릿정보를 수정할수 있는 기능구현

  5. 템플릿 정보를 삭제하는 기능 구현

  6. 템플릿 정보를 이용해서 추출된 이미지를 ocr 하는 기능 구현

  7. 템플릿 생성시에 저장한 좌표에 이름을 붙여서 저장할수 있게 하고, 해당이름과 ocr 한 결과를 받아서 엑셀(xlsx)로 만들어서 반환해주는 기능 구현

- 레이어드 아키텍쳐에 맞게 구현

  - presentation layer(디렉토리명 - view)

  - Business layer(디렉토리명 - service)

  - Persistence layer(디렉토리명 - models)

- pytest 라이브러리를 이용해서 단위 테스트 진행(디렉토리명 - test)


## 구성도 및 DB

![image](https://user-images.githubusercontent.com/56991244/164123085-4c1aa446-0c3b-4837-b378-3dd99589d91f.png)

![image](https://user-images.githubusercontent.com/56991244/164123092-da301840-8a46-470b-b58b-350af0f063ea.png)


## 결과물

#### 로그인 및 회원가입

![image](https://user-images.githubusercontent.com/56991244/164123114-75522a4a-cf88-432f-be97-66f26f38c625.png)

![image](https://user-images.githubusercontent.com/56991244/164123124-e6f6af02-fa3c-4160-9df1-845d7d53dbf9.png)

(시연영상)

https://user-images.githubusercontent.com/56991244/164124977-9c928da8-9409-4dba-a4c0-8d9d401d9b9f.mov


#### 일반 텍스트 추출 화면

![image](https://user-images.githubusercontent.com/56991244/164123151-d473fb81-345a-4a50-9dee-69b048f64a9e.png)

(시연영상)

https://user-images.githubusercontent.com/56991244/164125007-77eba9eb-33c7-480b-b3a5-b6a4077506f9.mov


#### 표추출 결과 화면 및 엑셀변환 결과

![image](https://user-images.githubusercontent.com/56991244/164123184-f6e1c589-0e58-4165-8285-ef3391423ec6.png)

![image](https://user-images.githubusercontent.com/56991244/164123194-c6bbf43b-62f7-430c-a8fc-8a28f6d61a64.png)

(시연영상)

https://user-images.githubusercontent.com/56991244/164125041-ee85c79a-a773-4f88-82fe-d04c0c269900.mov


#### 템플릿 결과 화면 - 원하는 위치만 ocr할 수 있는 기능

![image](https://user-images.githubusercontent.com/56991244/164123244-b99db808-b94f-4a33-8de3-94cddcfdff15.png)

![image](https://user-images.githubusercontent.com/56991244/164123250-65e31f9f-fc73-45a7-b2ec-a4e579f94fa3.png)

![image](https://user-images.githubusercontent.com/56991244/164123263-a42ca39d-b44b-40f3-8eb3-6e097d67ab77.png)

![image](https://user-images.githubusercontent.com/56991244/164123272-b466b36d-6aa5-443a-8ebe-a2759c5dae9f.png)

![image](https://user-images.githubusercontent.com/56991244/164123277-5e8f7625-216b-4c14-9c5e-bb1eeab90b0b.png)

(시연영상)

https://user-images.githubusercontent.com/56991244/164125076-dcb4fab9-f2e4-4d27-8c68-83a2ed4e59b4.mov




https://user-images.githubusercontent.com/56991244/164125089-b0b53f09-2979-42ce-9b53-79eec8ff4e91.mov

