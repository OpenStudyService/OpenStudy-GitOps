# 요구조건과 검증 상태

## 현재 범위

Terraform으로 AWS를 구성하고 DuckDNS에 EC2 공인 IP를 자동 반영한다.
Cloudflare는 수동 설정한다. 실제 배포와 연결 검증은 남아 있다.

| ID | 구성 | 상태 |
| --- | --- | --- |
| INF-NET-01 | `openstudy.duckdns.org`에 EC2 공인 IP 자동 반영 | 코드·모의 테스트 완료 |
| INF-NET-02 | 웹 서버의 HTTPS 인증서와 리디렉션 | 후속 작업 |
| INF-NET-03 | cloudflared 설치와 수동 Tunnel 연결 | 서버 코드 준비·연결 전 |
| INF-NET-04 | Cloudflare WAF·요청 제한 | 연결 조건 확인 필요 |
| INF-NET-05 | 기본 인바운드 차단·선택한 80·443 허용·Session Manager | 코드·모의 테스트 완료 |
| INF-SRV-01 | `t4g.small`·gp3 8GiB | 코드 준비·계정 혜택 확인 필요 |
| INF-SRV-02 | Docker·스왑 1GiB | 서버 코드 준비·컨테이너 배포 전 |
| INF-SRV-03 | 보안 업데이트·Asia/Seoul·시간 동기화 | 코드 준비·실환경 미검증 |

DNS는 사용자 요청에 따라 DuckDNS로 구성한다. 관리 접속은 SSH 대신 Session Manager를 사용한다.
INF-NET-04와 INF-SRV-03은 [원문 명세](https://docs.google.com/document/d/1RMxQHpqLZzPtN-OPuPSDGE3THKxtgHXNu4XbcZmbFSA/edit?tab=t.0)의 권장 항목이다.

## 로컬 검증

2026-10-16에 AWS 모의 테스트 6개, 이전 Cloudflare 예제 테스트 5개와 Python 테스트 9개를 통과했다.
ARM·x86 초기 설정의 Bash·Python 구문과 user data 크기 검사도 통과했다.
모의 테스트 통과는 실제 배포 성공을 뜻하지 않는다.

```sh
./scripts/validate.sh
```

## 다음 순서

1. [구축 절차](setup.md)로 AWS·DuckDNS 실제 연결을 확인한다.
2. 웹 서버, Gateway·Service 이미지와 Compose 파일을 작성한다.
3. HTTPS 응답과 외부 포트 차단을 확인한다.
4. [Cloudflare 연결 조건](cloudflare-manual.md)을 확인하고 수동 설정한다.
5. [GitOps 자동 배포](gitops.md)와 서버 시작·중지 자동화를 구현한다.
