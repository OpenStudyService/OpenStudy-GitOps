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

Cloudflare에서는 도메인 등록과 네임서버 위임을 먼저 완료한다.
대상 zone의 상태가 Active인지 확인한다.
Account ID, Zone ID, API 호스트명을 확인한다.
호스트명은 `api.example.com`과 같은 형식을 사용한다.

## 2. GitOps 연결 계약 확인

[GitOps 운영 설계](gitops.md)를 확인한다.
기본 연결 대상은 EC2의 `http://127.0.0.1:8080`이다.
Gateway는 후속 컨테이너 작업에서 이 주소에 연결한다.
Service와 DB는 호스트 포트를 공개하지 않는다.

이 단계에서는 애플리케이션 컨테이너를 생성하지 않는다.
Tunnel 연결 상태와 실제 애플리케이션 응답은 따로 검증한다.

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

인바운드 포트가 없는 보안 그룹과 최소 권한 EC2 역할을 생성한다.
EC2는 공인 IPv4로 아웃바운드 연결을 수행한다.
시작 시 OS 보안 업데이트, Docker 설치, 스왑과 시간 동기화를 설정한다.
서버 시간대는 `Asia/Seoul`을 사용한다.

현재 IAM 역할은 Session Manager와 지정한 Tunnel 토큰 읽기만 허용한다.
SSM Run Command, Patch Manager와 로그 외부 전송은 별도 구성 대상이다.
관리자는 자신의 IAM 권한으로 Session Manager에 접속한다.

## 5. Cloudflare 계획과 적용

대시보드에서 도메인과 API 토큰을 준비하는 방법은 [Terraform Cloudflare 설정 방법](cloudflare-terraform.md)을 따른다.

Cloudflare API 토큰에는 다음 권한을 대상 계정·zone으로 제한해 부여한다.

| 범위 | 권한 |
| --- | --- |
| Account | Cloudflare Tunnel: Edit |
| Zone | DNS: Edit |
| Zone | Zone Settings: Edit |
| Zone | Zone WAF: Edit — 요청 제한 규칙을 관리할 때 필요 |

토큰은 `CLOUDFLARE_API_TOKEN` 환경 변수로 전달한다.
Terraform 변수 파일에는 토큰을 넣지 않는다.
셸 이력에 토큰 값을 직접 기록하지 않는다.

```sh
cp terraform/cloudflare/terraform.tfvars.example terraform/cloudflare/terraform.tfvars
```

실제 `account_id`, `zone_id`, `hostname`을 설정한다.
`origin_service`가 Gateway의 로컬 수신 주소와 일치하는지 확인한다.
DNS CNAME 대상은 Tunnel ID를 사용한다. EC2 공인 IP를 DNS에 기록하지 않는다.
계획 단계에서 zone의 계정 소유권, 활성 상태와 호스트명 소속을 검사한다.

Full(strict)와 HTTPS 강제 이동은 zone 전체에 적용한다.
같은 zone의 다른 서비스도 이 설정을 지원하는지 확인한다.
기존에 Terraform으로 관리할 DNS나 zone 설정이 있으면 먼저 state로 import한다.

Cloudflare Free Managed Ruleset은 무료 플랜에서 기본 제공한다.
대시보드에서 해당 규칙의 적용 상태를 확인한다.
이 코드는 기존 관리형 WAF 규칙을 덮어쓰지 않는다.

요청 제한이 필요하면 실제 API 경로를 확인한 뒤 `enable_api_rate_limit = true`로 설정한다.
무료 플랜에 맞춰 규칙 하나와 10초 집계·차단 시간을 사용한다.
기본값은 `/api/` 경로에 대해 IP당 10초에 100회로 설정한다.
무료 플랜은 호스트 조건을 지원하지 않으므로 이 규칙은 zone 내 모든 호스트의 해당 경로에 적용한다.
기존 `http_ratelimit` 규칙 집합이 있으면 새로 생성하지 않는다. 먼저 import하고 기존 규칙을 구성에 보존한다.

```sh
terraform -chdir=terraform/cloudflare init
terraform -chdir=terraform/cloudflare plan -out=cloudflare.tfplan
terraform -chdir=terraform/cloudflare apply cloudflare.tfplan
```

## 6. Tunnel 토큰 등록

실행자는 `sts:GetCallerIdentity`와 대상 경로의 `ssm:PutParameter` 권한을 사용한다.
아래 스크립트는 Cloudflare에서 실행 토큰을 받아 Parameter Store에 SecureString으로 등록한다.
기본 AWS 관리형 SSM 키를 사용한다.
토큰은 권한 0600의 임시 파일로 전달한 뒤 파일을 삭제한다.
Terraform state나 EC2 user data에는 토큰을 기록하지 않는다.

```sh
python3 scripts/configure-tunnel.py \
  --account-id "$(terraform -chdir=terraform/cloudflare output -raw account_id)" \
  --tunnel-id "$(terraform -chdir=terraform/cloudflare output -raw tunnel_id)" \
  --parameter-name "$(terraform -chdir=terraform/aws output -raw tunnel_token_parameter_name)" \
  --aws-account-id "$(terraform -chdir=terraform/aws output -raw aws_account_id)" \
  --region "$(terraform -chdir=terraform/aws output -raw aws_region)"
```

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
sudo systemctl is-active docker chronyd amazon-ssm-agent cloudflared
sudo systemctl is-enabled docker chronyd amazon-ssm-agent cloudflared
swapon --show
timedatectl status
sudo ss -lntup
sudo journalctl -u cloudflared --since '-10 min' --no-pager
```

cloud-init 오류가 있으면 `/var/log/cloud-init-output.log`를 확인한다.
보안 업데이트에 재부팅이 필요한 경우 EC2를 재부팅하고 같은 검증을 반복한다.
SSH 데몬은 비활성 상태인지 확인한다.
서버 중지·시작 후에도 스왑과 서비스가 복구되는지 확인한다.

외부에서 다음 항목을 확인한다.

- DNS 조회 결과가 EC2 IP가 아닌 Cloudflare 프록시 주소인지 확인한다.
- HTTP 요청이 HTTPS로 이동하는지 확인한다.
- HTTPS 인증서와 Tunnel 연결 상태를 확인한다.
- EC2 공인 IP의 22·80·443·애플리케이션·DB 포트에 접속할 수 없는지 확인한다.

Gateway가 아직 없으면 도메인 요청에 502가 발생할 수 있다.
Gateway 배포 후 정상 응답까지 확인해야 전체 요청 경로 검증을 완료한다.

## state와 변경 관리

현재 AWS와 Cloudflare는 각각 별도의 로컬 state를 사용한다.
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

- [AWS EC2 프리티어 적용 기준](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html)
- [Session Manager 최소 권한 역할](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-create-iam-instance-profile.html)
- [Cloudflare 무료 관리형 WAF](https://developers.cloudflare.com/waf/get-started/)
- [Cloudflare 플랜별 요청 제한 기능](https://developers.cloudflare.com/waf/rate-limiting-rules/)
- [Cloudflare Tunnel 로컬 HTTP·HTTPS 연결](https://developers.cloudflare.com/tunnel/troubleshooting/https-origins/)
