# 네트워크·서버 요구조건 검증

## 상태 기준

공개 주소는 `https://openstudy.ddns.net`으로 유지한다.
DNS는 No-IP에서 관리한다. Cloudflare는 대시보드에서 수동 설정한다.
Terraform 적용 대상은 AWS로 한정한다.
사용자 확인 기준으로 Cloudflare는 아직 연결 전이다.

`코드 준비`는 Terraform 또는 초기 설정 파일을 작성한 상태를 뜻한다.
`실환경 미검증`은 실제 리소스 적용과 동작 확인이 남은 상태를 뜻한다.
모의 테스트 통과만으로 요구조건을 완료 처리하지 않는다.

## 검증표

| ID | 구성과 검증 방법 | 현재 상태 |
| --- | --- | --- |
| INF-NET-01 | No-IP DNS를 유지한다. Cloudflare의 외부 호스트 연결 조건과 실제 DNS 경로를 확인한다. | DNS 운영 기준 변경·Cloudflare 연결 전 |
| INF-NET-02 | 수동 연결 방식에 맞는 HTTPS 인증서와 리디렉션을 설정한다. 실제 호스트명으로 검증한다. | 수동 설정 예정·실환경 미검증 |
| INF-NET-03 | 대시보드에서 Tunnel을 만든다. cloudflared와 연결한 뒤 재시작 및 IP 직접 접근 차단을 확인한다. | 서버 코드 준비·Cloudflare 연결 전 |
| INF-NET-04 | 사용하는 Cloudflare 제품과 플랜의 WAF·요청 제한 지원 범위를 확인하고 수동 설정한다. | 적용 조건 확인 필요·실환경 미검증 |
| INF-NET-05 | 인바운드를 차단한다. SSH 대신 Session Manager를 사용한다. Service·DB 포트는 컨테이너 구성 시 추가 검증한다. | 네트워크 코드 준비·실환경 미검증 |
| INF-SRV-01 | EC2 t4g.small, gp3 8GiB를 기본 구성한다. 실제 계정의 혜택과 크레딧을 확인한다. | 코드 준비·계정 확인 필요 |
| INF-SRV-02 | Docker 부팅 활성화와 스왑 1~2GiB를 설정한다. 두 컨테이너의 자동 기동은 후속 Compose 작업에서 검증한다. | 서버 초기 설정 준비·컨테이너 구성 전 |
| INF-SRV-03 | AL2023 보안 업데이트, Asia/Seoul, chronyd를 설정한다. 재부팅 후 시간 동기화를 확인한다. | 코드 준비·실환경 미검증 |

INF-NET-04와 INF-SRV-03은 원문에서 권장 항목으로 분류한다.
INF-NET-01은 원문의 Cloudflare DNS 관리 대신 No-IP 유지로 변경한다.
Cloudflare에서 `openstudy.ddns.net`의 트래픽을 처리하는 경로는 별도로 검증한다.
INF-NET-05의 관리 접속은 SSH 키 인증 대신 포트를 열지 않는 Session Manager로 구성한다.
애플리케이션·DB 설치 후 외부 접근 차단을 다시 확인한다.

## 로컬 검증 기록

2026-10-16에 다음 로컬 검증을 완료했다.

AWS 모의 테스트 3개, Cloudflare 모의 테스트 5개와 토큰 처리 테스트 2개를 통과했다.
두 CPU 구조의 Bash 구문 검사와 user data 크기 검사도 통과했다.
Cloudflare 모의 테스트는 이전 Terraform 예제의 검사 기록이다.
현재 수동 연결 방식이나 `openstudy.ddns.net`의 연결 성공을 증명하지 않는다.

- Terraform 1.10.0을 사용한다.
- AWS 제공자 6.69.1과 Cloudflare 제공자 5.28.0을 lock 파일에 고정한다.
- 두 스택에 `terraform validate`와 모의 제공자 테스트를 적용한다.
- 인바운드 차단, IMDSv2, EBS 보존과 CPU 구조를 검사한다.
- DNS 프록시, TLS, Tunnel 경로와 무료 플랜 요청 제한을 검사한다.
- Cloudflare 계정이 다르거나 호스트명이 대상 zone에 속하지 않으면 계획을 중단하는지 검사한다.
- 두 CPU 구조의 부팅 스크립트를 렌더링해 Bash 구문과 user data 크기를 검사한다.
- 토큰 임시 파일 권한과 삭제, 출력 노출 방지, AWS 계정 불일치 차단을 검사한다.

## 실제 적용에 필요한 정보

- 유효한 AWS 자격증명과 대상 계정 ID를 확인한다.
- 계정 플랜, 혜택 만료일과 크레딧 잔액을 확인한다.
- Cloudflare 외부 호스트 연결 방식과 필요한 제공자 zone을 확인한다.
- No-IP 계정에서 필요한 CNAME과 소유권·인증서 검증을 설정할 수 있는지 확인한다.
- 대시보드에서 생성한 Tunnel 실행 토큰을 Parameter Store에 등록한다.
- 실제 Gateway 수신 포트와 API 경로를 확정한다.

초기 AWS STS 호출은 `InvalidClientTokenId` 오류로 실패했다.
실제 `terraform plan`과 `apply`는 인증 정보 확인 후 진행한다.
Cloudflare에는 Terraform을 적용하지 않는다.

## 후속 작업

1. Gateway·Service 이미지와 Compose 파일을 작성한다.
2. 내부 통신, 컨테이너 헬스체크와 재시작 정책을 검증한다.
3. GitOps pull, 부팅 동기화와 배포 이력을 구현한다.
4. 월·수·금 자동 시작·중지와 운영 검증을 수행한다.
