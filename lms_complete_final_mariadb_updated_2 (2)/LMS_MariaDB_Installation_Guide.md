# LMS (Learning Management System) MariaDB 설치 및 설정 가이드

이 문서는 LMS 애플리케이션에서 MariaDB를 데이터베이스로 사용하기 위한 설치 및 설정 방법을 안내합니다.

## 📋 목차

1.  MariaDB 서버 설치
2.  MariaDB 데이터베이스 및 사용자 생성
3.  LMS 애플리케이션 설정 변경
4.  LMS 데이터베이스 초기화

## 1. MariaDB 서버 설치

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install mariadb-server
```

### CentOS/RHEL

```bash
sudo yum install mariadb-server
sudo systemctl start mariadb
sudo systemctl enable mariadb
```

### macOS (Homebrew)

```bash
brew install mariadb
brew services start mariadb
```

### Windows

MariaDB 공식 웹사이트에서 설치 관리자(.msi)를 다운로드하여 설치합니다:
[https://mariadb.org/download/](https://mariadb.org/download/)

설치 시 `root` 비밀번호를 설정하고, `UTF-8` 인코딩을 기본으로 설정하는 것이 좋습니다.

## 2. MariaDB 데이터베이스 및 사용자 생성

MariaDB 서버가 설치 및 실행되었다면, 다음 단계를 따라 LMS에서 사용할 데이터베이스와 사용자를 생성합니다.

```bash
sudo mysql -u root -p
```

비밀번호를 입력하라는 메시지가 나타나면, MariaDB `root` 계정의 비밀번호(`wsuser`)를 입력합니다.
MariaDB 셸에 접속한 후 다음 SQL 명령어를 실행합니다:

```sql
CREATE DATABASE lms_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'wsuser'@'localhost' IDENTIFIED BY 'wsuser!';

GRANT ALL PRIVILEGES ON lms_db.* TO 'wsuser'@'localhost';

FLUSH PRIVILEGES;

EXIT;
```

**설명:**
- `lms_db`: LMS 애플리케이션이 사용할 데이터베이스 이름입니다.
- `lms_user`: LMS 애플리케이션이 데이터베이스에 접속할 사용자 이름입니다.
- `lms_password`: `lms_user`의 비밀번호입니다. **반드시 강력한 비밀번호로 변경하세요.**

## 3. LMS 애플리케이션 설정 변경

LMS 백엔드 프로젝트의 `.env` 파일에서 데이터베이스 연결 설정을 MariaDB로 변경해야 합니다.

`lms_backend/.env` 파일을 열고 `DATABASE_URL` 라인을 다음과 같이 수정합니다:

```
DATABASE_URL=mysql+pymysql://wsuser:wsuser!@localhost:3306/lms_db?charset=utf8mb4
```

**참고:**
- `lms_user`와 `lms_password`는 2단계에서 설정한 값으로 변경해야 합니다.
- `localhost:3306`은 MariaDB 서버의 주소와 포트입니다. MariaDB가 다른 호스트나 포트에서 실행 중이라면 해당 값으로 변경하세요.

## 4. LMS 데이터베이스 초기화

MariaDB 설정이 완료되었다면, LMS 애플리케이션의 데이터베이스를 초기화하고 필요한 테이블과 초기 데이터를 생성합니다.

`lms_backend` 디렉토리로 이동하여 다음 명령어를 실행합니다:

```bash
cd /path/to/your/lms_backend
python init_db.py
```

이 스크립트는 MariaDB에 LMS에 필요한 모든 테이블을 생성하고, 기본 역할(admin, instructor, student)과 테스트 계정을 삽입합니다.

## 5. LMS 애플리케이션 실행

모든 설정이 완료되었다면, LMS 애플리케이션을 실행합니다.

```bash
cd /path/to/your/lms_backend
python src/main.py
```

이제 브라우저에서 `http://localhost:5004`로 접속하여 MariaDB를 사용하는 LMS를 확인할 수 있습니다.

---

**주의:** 프로덕션 환경에서는 `root` 계정 사용을 피하고, `lms_user`의 비밀번호를 더욱 강력하게 설정하며, 네트워크 보안을 강화해야 합니다.

