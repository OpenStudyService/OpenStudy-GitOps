# OpenStudy-Infra

OpenStudy의 AWS 네트워크와 서버를 Terraform으로 관리한다.
1차 작업 범위는 `INF-NET-01~05`, `INF-SRV-01~03`으로 한다.
GitOps 운영 설계와 Terraform 구성을 함께 관리한다.
애플리케이션 배포 방식은 [GitOps 운영 설계](docs/gitops.md)를 따른다.

## 구성

- AWS 서울 리전에 VPC, 퍼블릭 서브넷, 인터넷 게이트웨이를 구성한다.
- EC2 1대를 사용한다. 기본값은 ARM 기반 `t4g.small`이다.
- 보안 그룹은 기본적으로 인바운드 포트를 닫는다. 필요하면 Terraform 변수로 80·443만 허용한다.
- 관리 접속은 Session Manager를 사용한다.
- Docker, 스왑, 시간 동기화와 cloudflared 서비스를 초기 설정한다.
- 호스트명은 `openstudy.duckdns.org`을 사용한다. EC2 공인 IPv4를 DuckDNS에 자동 반영한다.
- Terraform이 부팅 시 갱신과 15분 간격의 IP 확인을 구성한다. 토큰은 AWS Parameter Store에서 읽는다.
- Cloudflare HTTPS·WAF와 Tunnel을 추가하는 경우 대시보드에서 수동 설정한다.

공인 IPv4는 패키지 설치와 Tunnel·Session Manager의 아웃바운드 연결에 사용한다.
현재 DNS 경로는 `openstudy.duckdns.org → EC2 공인 IPv4`로 한다.
웹 서버와 HTTPS 인증서는 후속 컨테이너 단계에서 구성한다.
Cloudflare는 연결 전이다. DNS 자동 갱신은 Cloudflare 연결과 별도로 동작한다.
NAT Gateway, 로드 밸런서와 Elastic IP는 생성하지 않는다.

## 디렉터리

```text
terraform/aws/          AWS 네트워크·EC2·IAM
terraform/cloudflare/   이전 Cloudflare Terraform 예제·현재 배포에서 미사용
scripts/               DuckDNS 자동 갱신, Tunnel 토큰 등록과 로컬 검증
docs/                  구축 순서와 요구조건 검증
```

## 작업 순서

1. GitOps 운영 설계와 Gateway 연결 계약을 확인한다.
2. AWS 계정, 프리티어 적용 범위와 DuckDNS 계정의 `openstudy` 등록을 확인한다.
3. AWS Terraform을 계획하고 적용한다.
4. DuckDNS 토큰을 Parameter Store에 등록한다.
5. EC2 공인 IP와 DuckDNS의 DNS 응답이 일치하는지 확인한다.
6. Cloudflare를 사용할 경우 별도의 수동 설정과 Tunnel 검증을 수행한다.
7. 후속 작업에서 Gateway·Service 컨테이너를 배포하고 도메인 요청을 검증한다.

세부 명령은 [구축 절차](docs/setup.md)를 따른다.
IP 자동 연동은 [DuckDNS 설정 방법](docs/duckdns.md)을 따른다.
Cloudflare는 [수동 설정 범위](docs/cloudflare-manual.md)를 따른다.
완료 여부는 [요구조건 검증표](docs/requirements.md)에 기록한다.

## 로컬 검증

Terraform 1.10 이상, Python 3.9 이상, Bash를 사용한다.

```sh
./scripts/validate.sh
```

모의 제공자를 사용하는 Terraform 테스트는 실제 클라우드 리소스를 생성하지 않는다.
검증 스크립트는 이전 Cloudflare 예제도 모의 검사한다. 실제 적용 대상은 `terraform/aws`로 한정한다.
로컬 검증 성공은 실제 배포 성공을 뜻하지 않는다.

## 현재 상태

실제 AWS·Cloudflare 적용은 완료 전이다.
최초 점검에서 AWS 인증이 `InvalidClientTokenId` 오류로 실패했다.
DuckDNS 갱신 코드와 Terraform 구성은 준비했다. 실제 EC2에서의 DNS 갱신 검증은 남아 있다.
Cloudflare 연결은 아직 진행하지 않았다.

## 참고 문서

- [OpenStudy 인프라 요구조건 명세서](https://docs.google.com/document/d/1RMxQHpqLZzPtN-OPuPSDGE3THKxtgHXNu4XbcZmbFSA/edit?tab=t.0)
- [AWS EC2 프리티어 적용 기준](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [DuckDNS API 명세](https://www.duckdns.org/spec.jsp)
- [Cloudflare 외부 호스트 연결 안내](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/start/getting-started/)
