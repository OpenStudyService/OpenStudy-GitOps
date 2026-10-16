# OpenStudy GitOps 운영 설계

## 목적과 상태

Git에 기록한 배포 설정을 기준으로 서버의 컨테이너 상태를 맞춘다.
서버가 설정을 가져오는 pull 방식을 사용한다.
서버가 꺼진 동안 병합한 변경도 다음 부팅 때 적용한다.

이 문서는 배포 설계와 운영 절차를 정의한다.
현재 애플리케이션용 Compose 파일과 동기화 스크립트는 구현 전이다.
AWS 네트워크와 서버는 이 저장소의 Terraform으로 구성한다.
공개 호스트명은 `openstudy.duckdns.org`을 사용한다.
서버가 EC2 공인 IPv4를 DuckDNS에 자동 반영한다.
Cloudflare를 추가할 경우 대시보드에서 수동 설정한다.

## 저장소 역할

| 저장소 | 관리 대상 |
| --- | --- |
| OpenStudy-Infra | AWS Terraform, Cloudflare 수동 설정 문서, 서버 초기 설정과 GitOps 운영 절차 |
| 애플리케이션 저장소 | Gateway·Service 소스, 검사·테스트, 이미지 빌드 |

Compose 배포 설정과 이미지 버전도 후속 단계에서 이 저장소에 추가한다.

Terraform 실행으로 애플리케이션을 배포하지 않는다.
GitOps 동기화 작업으로 인프라를 생성하거나 삭제하지 않는다.

## 요청 경로

```text
현재 DNS 경로: openstudy.duckdns.org → EC2 공인 IPv4

Cloudflare 추가 시 목표 요청 경로:
사용자 → Cloudflare HTTPS·WAF → Cloudflare Tunnel
       → EC2의 cloudflared → 로컬 API Gateway → 내부 Service
```

Cloudflare는 아직 연결 전이다.
외부 호스트 연결과 인증서 검증을 마친 뒤 목표 요청 경로를 확인한다.
연결 조건은 [Cloudflare 수동 설정](cloudflare-manual.md)을 따른다.

EC2 보안 그룹은 기본적으로 인바운드를 차단한다.
직접 웹 접속은 `web_ingress_cidrs`로 TCP 80·443만 허용할 수 있다.
웹 수신 서비스와 HTTPS 인증서는 별도로 구성한다.
서버 관리는 AWS Systems Manager Session Manager로 수행한다.
SSH 포트와 SSH 키를 사용하지 않는다.

cloudflared는 호스트의 systemd 서비스로 실행한다.
Gateway는 `127.0.0.1:8080`에만 포트를 연결하는 것을 기본 계약으로 한다.
실제 Gateway 포트가 다르면 Cloudflare 대시보드의 Service URL도 함께 변경한다.
Service와 DB의 포트는 호스트에 공개하지 않는다.
DB 실행 위치는 별도로 확정한다.

Cloudflare에서 EC2까지의 구간은 Tunnel로 암호화한다.
기본 로컬 구간인 cloudflared → Gateway는 루프백 HTTP를 사용한다.
Cloudflare의 TLS 설정은 이 로컬 HTTP 구간을 HTTPS로 바꾸지 않는다.

## 배포 순서

1. 애플리케이션 PR에서 검사와 테스트를 실행한다.
2. 병합한 소스로 서버 CPU 구조에 맞는 이미지를 빌드한다. `t4g.small`은 `linux/arm64`를 사용한다.
3. 이미지를 레지스트리에 올린다. 커밋 SHA 등 변경하지 않는 버전 태그를 사용한다.
4. 이 저장소의 해당 애플리케이션 이미지 버전을 변경한다.
5. 서버가 기본 브랜치의 확정된 커밋을 가져온다.
6. Compose 설정을 검증한 뒤 변경한 이미지를 내려받고 컨테이너를 갱신한다.
7. Gateway와 Service의 헬스체크를 확인한다. 성공한 커밋 SHA를 배포 이력에 기록한다.

Gateway와 Service의 이미지 버전은 따로 관리한다.
각 배포에서는 해당 애플리케이션의 버전만 변경한다.
레지스트리 주소와 헬스체크 경로는 애플리케이션 구성 단계에서 확정한다.

## 서버 동기화 계약

- 작업 디렉터리는 `/opt/openstudy`를 사용한다.
- 서버 부팅 시와 운영 중 일정 간격으로 동기화한다. 실행 간격은 동기화 구현 단계에서 확정한다.
- 동기화 잠금을 사용해 두 배포가 동시에 실행되지 않게 한다.
- 설정 검증과 이미지 다운로드가 성공한 뒤 컨테이너를 갱신한다.
- 컨테이너에는 재시작 정책, 헬스체크, 로그 용량 제한을 설정한다.
- 저장소가 비공개이면 읽기 전용 Deploy Key 등 최소 권한 인증을 사용한다.
- 인증 오류나 배포 실패는 systemd 로그에 기록한다. 인증값은 로그에 기록하지 않는다.

## 비밀값 관리

애플리케이션 비밀값은 서버의 `/etc/openstudy` 아래 권한을 제한한 파일에 둔다.
Git에는 실제 `.env`, 비밀번호, 인증서 개인 키, 토큰을 저장하지 않는다.

Tunnel 실행 토큰은 AWS Systems Manager Parameter Store의 SecureString으로 저장한다.
EC2 역할은 지정한 경로의 토큰만 읽을 수 있게 한다.
토큰 값은 Terraform 변수, state, EC2 user data에 넣지 않는다.

DuckDNS 토큰은 별도의 SecureString에 저장한다.
서버는 부팅 후와 약 15분 간격으로 공인 IP를 확인한다.
IP가 바뀌면 DNS를 갱신한다. 설정은 [DuckDNS 연동 문서](duckdns.md)를 따른다.

## 이전 버전 복구

1. 마지막 정상 배포 커밋과 이미지 버전을 확인한다.
2. 문제가 발생한 배포 설정 커밋을 `git revert`로 되돌린다.
3. 복구 변경을 병합한다.
4. 서버 동기화 후 헬스체크와 실제 요청을 확인한다.

긴급 수동 복구를 수행한 경우에도 같은 이미지 버전을 Git에 기록한다.
DB 스키마 변경은 별도의 호환성 검토를 거친다. 이미지 복구만으로 DB를 되돌릴 수 있다고 가정하지 않는다.

## 작업 순서

1. 네트워크·서버: DNS·TLS·WAF·Tunnel, EC2, 스왑과 관리 접속을 구성한다.
2. 컨테이너: 실제 이미지와 Compose 파일, 내부 통신, 헬스체크를 구성한다.
3. 자동 배포: 이미지 버전 갱신, 서버 pull, 부팅 동기화를 구현한다.
4. 운영: 자동 시작·중지, DB 유지, 로그와 장애 대응을 검증한다.

1단계의 코드 작성과 실제 인프라 적용은 구분해 기록한다.
컨테이너가 없는 상태의 HTTP 502 응답을 배포 성공으로 판단하지 않는다.

## 참고 문서

- [OpenStudy 인프라 요구조건 명세서](https://docs.google.com/document/d/1RMxQHpqLZzPtN-OPuPSDGE3THKxtgHXNu4XbcZmbFSA/edit?tab=t.0)
- [Cloudflare Tunnel의 로컬 HTTP·HTTPS 구간](https://developers.cloudflare.com/tunnel/troubleshooting/https-origins/)
