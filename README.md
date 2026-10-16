# OpenStudy-Infra

OpenStudy의 AWS 네트워크와 EC2를 Terraform으로 관리한다.
`openstudy.duckdns.org`을 EC2 공인 IP에 자동 연결한다.

## 기본 구성

- 서울 리전에 `t4g.small` 1대, gp3 8GiB, 스왑 1GiB를 구성한다.
- Docker와 DuckDNS 자동 갱신 서비스를 설치한다.
- 서버 관리는 AWS Session Manager를 사용한다.
- 인바운드 포트는 기본 차단한다. 필요하면 TCP 80·443을 허용한다.

## 실행 순서

1. DuckDNS에서 `openstudy`를 등록하고 토큰을 확인한다.
2. AWS 인증과 계정의 프리티어·크레딧을 확인한다.
3. `terraform/aws/terraform.tfvars`에 계정 ID를 설정한다.
4. Terraform으로 EC2를 생성한다.
5. DuckDNS 토큰을 AWS Parameter Store에 저장한다.
6. EC2에서 갱신 서비스를 실행하고 DNS 응답을 확인한다.

명령은 **[처음부터 따라 하는 구축 절차](docs/setup.md)**를 따른다.
이후 부팅 시와 약 15분 간격으로 IP를 확인하고 변경 시 DNS를 갱신한다.

## 추가 문서

- [DuckDNS 토큰 변경과 오류 해결](docs/duckdns.md)
- [Cloudflare 추가 설정](docs/cloudflare-manual.md)
- [GitOps 배포 순서](docs/gitops.md)
- [요구조건과 검증 상태](docs/requirements.md)

전체 로컬 검증은 `./scripts/validate.sh`로 실행한다.
현재 코드는 준비한 상태다. 실제 AWS 배포와 DNS 연결 확인은 남아 있다.
웹 서버·HTTPS·Cloudflare 연결은 후속 작업으로 진행한다.
