# OpenStudy GitOps

OpenStudy 서비스의 인프라와 배포 설정을 관리한다.
서버가 Git에 저장한 설정을 가져와 적용하는 **pull 방식 GitOps**를 사용한다.
컨테이너 실행 설정과 이미지 버전을 Git으로 관리해 배포 이력을 추적한다.

현재 초기 구성 단계다. 아래 내용은 인프라 요구조건 명세서에 따른 구축 계획을 설명한다.

## 인프라 구성

- **Cloudflare**: DNS와 HTTPS를 담당한다. Cloudflare Tunnel로 서버에 연결한다.
- **AWS EC2 1대**: API Gateway와 Service 컨테이너를 실행한다.
- **API Gateway**: 외부 요청을 받아 내부 Service로 전달한다.
- **Service·DB**: 외부에 포트를 공개하지 않는다. DB 실행 위치는 추후 확정한다.

## 배포 방식

1. 각 애플리케이션 저장소의 GitHub Actions에서 검사·테스트·이미지 빌드를 수행한다.
2. 빌드한 이미지를 레지스트리에 올리고 배포 설정의 이미지 버전 태그를 갱신한다.
3. 서버가 Git의 최신 배포 설정을 가져와 컨테이너에 적용한다.

서버 부팅 시에도 배포 설정을 동기화한다. Gateway와 Service는 각각 독립적으로 배포한다.
이전 버전으로 복구할 때는 Git의 배포 설정을 되돌린다.

## 운영 원칙

- 서버는 월·수·금 하루 5시간만 가동하도록 구성한다.
- 컨테이너에 헬스체크와 자동 재시작 정책을 설정한다.
- 비밀번호와 토큰은 서버 환경 변수 또는 시크릿 파일로 관리한다. 저장소에는 저장하지 않는다.

## 참고 문서

[OpenStudy 인프라 요구조건 명세서](https://docs.google.com/document/d/1RMxQHpqLZzPtN-OPuPSDGE3THKxtgHXNu4XbcZmbFSA/edit?tab=t.0)
