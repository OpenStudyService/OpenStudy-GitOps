# 네트워크·서버 구축 절차

## 1. 배포 대상 확인

AWS CLI v2, Terraform 1.10 이상, Python 3.9 이상을 준비한다.
AWS 프로필과 리전은 실제 OpenStudy 계정에 맞춘다.

```sh
aws sts get-caller-identity
aws configure get region
aws ec2 describe-instance-types \
  --region ap-northeast-2 \
  --instance-types t4g.small t3.micro \
  --query 'InstanceTypes[].{Type:InstanceType,FreeTierEligible:FreeTierEligible,Architecture:ProcessorInfo.SupportedArchitectures}'
```

STS가 실패하면 로컬 AWS 자격증명을 갱신한다.
액세스 키와 비밀 키는 문서나 채팅에 기록하지 않는다.

Billing에서 계정 플랜, 혜택 만료일, 크레딧 잔액을 확인한다.
계정 가입일과 `FreeTierEligible` 표시만으로 실제 무료 사용을 보장할 수 없다.
2025-07-15 이후 가입 계정은 `t4g.small`을 프리티어 대상 유형으로 표시한다.
이전 계정의 기존 12개월 혜택은 만료 여부를 따로 확인한다.
`t3.micro`도 혜택이 만료된 계정에서는 무료라고 가정하지 않는다.
EBS와 공인 IPv4 등 함께 생성하는 리소스의 비용도 확인한다.

공개 호스트명은 `openstudy.duckdns.org`을 사용한다.
본인 DuckDNS 계정에 `openstudy`를 등록하고 토큰을 준비한다.
EC2 공인 IP 자동 갱신은 [DuckDNS 설정 문서](duckdns.md)를 따른다.
Cloudflare는 아직 연결 전이다. 추가할 경우 대시보드에서 설정한다.

## 2. GitOps 연결 계약 확인

[GitOps 운영 설계](gitops.md)를 확인한다.
기본 연결 대상은 EC2의 `http://127.0.0.1:8080`이다.
Gateway는 후속 컨테이너 작업에서 이 주소에 연결한다.
Service와 DB는 호스트 포트를 공개하지 않는다.

이 단계에서는 애플리케이션 컨테이너를 생성하지 않는다.
Tunnel 연결 상태와 실제 애플리케이션 응답은 따로 검증한다.
EC2 직접 접속을 사용하려면 80·443 수신 서비스와 HTTPS 인증서를 별도로 구성한다.

## 3. 로컬 검증

저장소 루트에서 실행한다.

```sh
./scripts/validate.sh
```

검증은 형식 검사, 제공자 스키마 검사, Terraform 모의 테스트를 수행한다.
두 CPU 구조의 초기 설정 스크립트와 토큰 등록 코드도 검사한다.
실제 AWS·Cloudflare 리소스는 생성하지 않는다.

## 4. AWS 계획과 적용

```sh
cp terraform/aws/terraform.tfvars.example terraform/aws/terraform.tfvars
```

`terraform.tfvars`에서 실제 계정 ID를 설정한다.
프리티어 검토가 끝난 뒤 `free_tier_confirmed = true`로 설정한다.
기본 구성은 `t4g.small`, gp3 8GiB, 스왑 1GiB를 사용한다.
`t3.micro`를 선택하면 AMI와 cloudflared RPM도 x86으로 변경한다.

```sh
terraform -chdir=terraform/aws init
terraform -chdir=terraform/aws plan -out=aws.tfplan
terraform -chdir=terraform/aws apply aws.tfplan
terraform -chdir=terraform/aws output
```

기본 보안 그룹은 인바운드를 차단한다.
직접 웹 접속이 필요하면 `web_ingress_cidrs`에 허용할 IPv4 CIDR을 지정한다.
이 설정은 TCP 80·443만 허용한다.
EC2는 공인 IPv4로 아웃바운드 연결을 수행한다.
시작 시 OS 보안 업데이트, Docker 설치, 스왑과 시간 동기화를 설정한다.
서버 시간대는 `Asia/Seoul`을 사용한다.

EC2 역할은 Session Manager와 지정한 Tunnel 토큰 읽기를 허용한다.
DuckDNS를 활성화하면 지정한 DuckDNS 토큰 읽기도 허용한다.
SSM Run Command, Patch Manager와 로그 외부 전송은 별도 구성 대상이다.
관리자는 자신의 IAM 권한으로 Session Manager에 접속한다.

## 5. DuckDNS 토큰 등록

기본값은 `enable_duckdns = true`, `duckdns_subdomain = "openstudy"`이다.
파라미터 경로를 확인한다.

```sh
terraform -chdir=terraform/aws output -raw duckdns_token_parameter_name
```

AWS Parameter Store에서 위 경로에 Standard 등급의 SecureString을 생성한다.
기본 경로는 `/openstudy-prod/duckdns/token`이다.
기본 AWS 관리형 SSM 키를 사용한다.
값에는 DuckDNS 계정의 token 문자열만 입력한다.
토큰을 Terraform 변수나 Git에 기록하지 않는다.

서버는 부팅 후와 약 15분 간격으로 공인 IPv4를 확인한다.
IP가 변경되면 DuckDNS에 반영한다.
상세 설정과 확인 명령은 [DuckDNS와 EC2 연동](duckdns.md)을 따른다.

## 6. Cloudflare 수동 설정: 추가 사용 시

현재 DNS는 EC2를 직접 가리킨다. DuckDNS 등록만으로 Cloudflare를 경유하지 않는다.
Cloudflare를 추가하려면 [수동 설정 문서](cloudflare-manual.md)의 연결 조건을 먼저 확인한다.
Tunnel의 Gateway 연결 대상은 `http://127.0.0.1:8080`으로 한다.

Terraform은 AWS에만 적용한다.
`terraform/cloudflare`는 이전 예제로 보관한다. 현재 배포에서는 적용하지 않는다.

### Tunnel 토큰 등록

Cloudflare 대시보드에서 만든 Tunnel의 실행 토큰을 사용한다.
AWS Parameter Store에 SecureString으로 등록한다.
파라미터 경로는 다음 명령으로 확인한다.

```sh
terraform -chdir=terraform/aws output -raw tunnel_token_parameter_name
```

AWS 콘솔에서 위 경로에 Standard 등급의 SecureString을 생성한다.
기본 AWS 관리형 SSM 키를 사용한다.
값에는 Tunnel 토큰만 입력한다. Cloudflare의 설치 명령 전체를 입력하지 않는다.
토큰은 Terraform 변수, state, EC2 user data나 Git에 기록하지 않는다.
Cloudflare Terraform의 output은 사용하지 않는다.

EC2의 cloudflared 서비스는 시작할 때 토큰을 읽는다.
최초 토큰 등록 전에는 30초마다 다시 시작한다.
토큰 등록 후 Tunnel이 Healthy 상태가 되는지 확인한다.
토큰을 교체한 경우에는 서버에서 `sudo systemctl restart cloudflared`를 실행한다.

## 7. 서버 검증

AWS 콘솔의 Session Manager 또는 로컬 Session Manager 플러그인으로 접속한다.
CLI를 사용하는 경우 다음 명령을 실행한다.

```sh
aws ssm start-session \
  --region "$(terraform -chdir=terraform/aws output -raw aws_region)" \
  --target "$(terraform -chdir=terraform/aws output -raw instance_id)"
```

서버 안에서 다음 명령을 실행한다.

```sh
sudo cloud-init status --wait
sudo systemctl is-active docker chronyd amazon-ssm-agent openstudy-duckdns.timer
sudo systemctl is-enabled docker chronyd amazon-ssm-agent openstudy-duckdns.timer
swapon --show
timedatectl status
sudo ss -lntup
sudo journalctl -u openstudy-duckdns.service --since '-30 min' --no-pager
```

cloud-init 오류가 있으면 `/var/log/cloud-init-output.log`를 확인한다.
보안 업데이트에 재부팅이 필요한 경우 EC2를 재부팅하고 같은 검증을 반복한다.
SSH 데몬은 비활성 상태인지 확인한다.
서버 중지·시작 후에도 스왑과 서비스가 복구되는지 확인한다.

외부에서 다음 항목을 확인한다.

- `dig +short openstudy.duckdns.org A`의 결과와 현재 EC2 공인 IPv4를 비교한다.
- 22·애플리케이션·DB 포트의 외부 접근이 차단되는지 확인한다.
- 80·443은 `web_ingress_cidrs`에 지정한 범위에서만 접근할 수 있는지 확인한다.
- 웹 서버와 인증서를 구성한 뒤 HTTPS 응답과 HTTP 리디렉션을 확인한다.

Cloudflare를 추가한 경우에는 cloudflared 서비스와 Tunnel 연결 상태도 확인한다.
Gateway가 아직 없으면 Tunnel 요청에 502가 발생할 수 있다.
Gateway 배포 후 정상 응답까지 확인해야 전체 요청 경로 검증을 완료한다.

## state와 변경 관리

현재 적용 대상인 AWS는 로컬 state를 사용한다.
이전 Cloudflare 코드와 state가 있다면 수동 설정 전환 중 자동 삭제하지 않는다.
state, 계획 파일과 실제 변수 파일은 Git에서 제외한다.
적용 작업은 같은 state를 유지하는 작업 환경에서 수행한다.
여러 작업자가 적용하기 전에는 암호화와 잠금을 사용하는 원격 backend로 전환한다.

EC2는 종료 방지와 Terraform `prevent_destroy`를 설정한다.
루트 EBS는 종료 시 삭제하지 않게 설정한다.
서버 운영 중단에는 종료 대신 중지를 사용한다.

최초 AMI는 AWS 공식 AL2023 SSM 경로에서 선택한다.
이후 새 AMI 게시만으로 서버를 교체하지 않게 한다.
초기 설정 스크립트 변경은 서버 교체가 필요하므로 `prevent_destroy`가 자동 교체를 막는다.
기존 서버의 변경은 내용을 검토한 뒤 Session Manager로 적용한다.

월·수·금 자동 시작·중지와 애플리케이션 배포는 후속 작업에서 구현한다.
현재 코드는 서버 가동 시간을 자동으로 제한하지 않는다.

## 출처

- [DuckDNS API 명세](https://www.duckdns.org/spec.jsp)
- [AWS EC2 프리티어 적용 기준](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [Session Manager 최소 권한 역할](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-create-iam-instance-profile.html)
- [Cloudflare 무료 관리형 WAF](https://developers.cloudflare.com/waf/get-started/)
- [Cloudflare 플랜별 요청 제한 기능](https://developers.cloudflare.com/waf/rate-limiting-rules/)
- [Cloudflare Tunnel 로컬 HTTP·HTTPS 연결](https://developers.cloudflare.com/tunnel/troubleshooting/https-origins/)
