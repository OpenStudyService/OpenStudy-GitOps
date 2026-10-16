# OpenStudy-Infra

OpenStudy의 네트워크와 서버를 Terraform으로 관리한다.
1차 작업 범위는 `INF-NET-01~05`, `INF-SRV-01~03`으로 한다.
GitOps 운영 설계와 Terraform 구성을 함께 관리한다.
애플리케이션 배포 방식은 [GitOps 운영 설계](docs/gitops.md)를 따른다.

## 구성

- AWS 서울 리전에 VPC, 퍼블릭 서브넷, 인터넷 게이트웨이를 구성한다.
- EC2 1대를 사용한다. 기본값은 ARM 기반 `t4g.small`이다.
- 보안 그룹의 인바운드 포트는 모두 닫는다. 관리 접속은 Session Manager를 사용한다.
- Docker, 스왑, 시간 동기화와 cloudflared 서비스를 초기 설정한다.
- Cloudflare의 기존 도메인에 프록시 DNS, Full(strict), HTTPS 리디렉션과 Tunnel을 설정한다.
- Free Managed Ruleset 적용 상태를 확인한다. 필요한 경우 무료 플랜 범위의 요청 제한 규칙 하나를 추가한다.

공인 IPv4는 패키지 설치와 Tunnel·Session Manager의 아웃바운드 연결에 사용한다.
외부 요청은 Cloudflare Tunnel로 수신한다.
NAT Gateway, 로드 밸런서와 Elastic IP는 생성하지 않는다.

## 디렉터리

```text
terraform/aws/          AWS 네트워크·EC2·IAM
terraform/cloudflare/   DNS·TLS·Tunnel·선택 요청 제한
scripts/               토큰 등록과 로컬 검증
docs/                  구축 순서와 요구조건 검증
```

## 작업 순서

1. GitOps 운영 설계와 Gateway 연결 계약을 확인한다.
2. AWS 계정, 프리티어 적용 범위와 Cloudflare 도메인을 확인한다.
3. AWS Terraform을 계획하고 적용한다.
4. Cloudflare Terraform을 계획하고 적용한다.
5. Tunnel 토큰을 Parameter Store에 등록한다.
6. 서버 초기 설정과 Tunnel 연결을 검증한다.
7. 후속 작업에서 Gateway·Service 컨테이너를 배포하고 도메인 요청을 검증한다.

세부 명령은 [구축 절차](docs/setup.md)를 따른다.
완료 여부는 [요구조건 검증표](docs/requirements.md)에 기록한다.

## 로컬 검증

Terraform 1.10 이상, Python 3.9 이상, Bash를 사용한다.

```sh
./scripts/validate.sh
```

모의 제공자를 사용하는 Terraform 테스트는 실제 클라우드 리소스를 생성하지 않는다.
로컬 검증 성공은 실제 배포 성공을 뜻하지 않는다.

## 현재 상태

실제 AWS·Cloudflare 적용은 완료 전이다.
최초 점검에서 AWS 인증이 `InvalidClientTokenId` 오류로 실패했다.
Cloudflare 도메인과 인증 정보도 확인이 필요하다.

## 참고 문서

- [OpenStudy 인프라 요구조건 명세서](https://docs.google.com/document/d/1RMxQHpqLZzPtN-OPuPSDGE3THKxtgHXNu4XbcZmbFSA/edit?tab=t.0)
- [AWS EC2 프리티어 적용 기준](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [Cloudflare Tunnel Terraform 안내](https://developers.cloudflare.com/tunnel/guides/terraform/)
