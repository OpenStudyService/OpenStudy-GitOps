# Terraform으로 Cloudflare 설정하기

## 목적

OpenStudy의 DNS, HTTPS와 Tunnel을 설정한다.
이 문서의 명령은 `OpenStudy-Infra` 저장소 루트에서 실행한다.
Terraform 1.10 이상을 사용한다.

이 저장소는 Cloudflare 제공자 5.x를 사용한다.
설치 버전은 `terraform/cloudflare/.terraform.lock.hcl`을 따른다.

## 1. 도메인 준비

1. [Cloudflare 대시보드](https://dash.cloudflare.com)에 로그인한다.
2. `Domains`에서 `Onboard a domain`을 선택한다.
3. 보유한 기본 도메인을 입력한다. 예시는 `example.com`으로 한다.
4. Free 플랜을 선택한다.
5. 기존 웹·메일 서비스의 DNS 레코드가 옮겨졌는지 확인한다.
6. 도메인을 구매한 업체에서 네임서버를 Cloudflare가 안내한 값으로 변경한다.
7. Cloudflare에서 도메인 상태가 `Active`인지 확인한다.

Cloudflare Registrar에서 구매한 도메인은 Cloudflare 네임서버를 기본 사용한다.
세부 절차는 [도메인 연결 안내](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/)를 따른다.

Terraform은 이미 등록한 도메인을 사용한다.
도메인 구매와 네임서버 변경은 이 코드의 관리 범위에 포함하지 않는다.

## 2. Account ID와 Zone ID 확인

Cloudflare에서 도메인 하나의 DNS 관리 영역을 zone이라고 한다.

1. 대시보드에서 대상 도메인을 선택한다.
2. `Overview` 화면 아래쪽의 `API` 영역을 찾는다.
3. `Account ID`와 `Zone ID`를 각각 복사한다.

두 값은 모두 32자리 식별자지만 용도가 다르다.
Account ID는 계정을 구분한다. Zone ID는 도메인을 구분한다.
화면 위치는 [식별자 확인 안내](https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/)를 참고한다.

## 3. Terraform용 API 토큰 생성

1. `My Profile` → `API Tokens`로 이동한다.
2. `Create Token`에서 사용자 지정 토큰을 선택한다.
3. 이름을 `OpenStudy Terraform`으로 입력한다.
4. 다음 권한을 추가한다.

| 범위 | 권한 | 용도 |
| --- | --- | --- |
| Account | Cloudflare Tunnel: Edit | Tunnel 생성과 연결 설정 |
| Zone | DNS: Edit | 프록시 CNAME 생성 |
| Zone | Zone Settings: Edit | Full(strict)와 HTTPS 강제 이동 |
| Zone | Zone WAF: Edit | 선택 요청 제한 규칙을 사용할 때 추가 |

5. `Account Resources`는 OpenStudy를 운영할 계정으로 제한한다.
6. `Zone Resources`는 대상 도메인으로 제한한다.
7. 권한 요약을 확인한 뒤 토큰을 생성한다.
8. 한 번 표시되는 토큰 값을 비밀번호 관리자 등 안전한 위치에 보관한다.

절차와 권한 범위는 [API 토큰 생성 안내](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/)를 참고한다.

### 두 토큰의 차이

| 토큰 | 역할 | 보관 위치 |
| --- | --- | --- |
| Cloudflare API 토큰 | Terraform이 Cloudflare 설정을 관리한다. | 작업자의 환경 변수 |
| Tunnel 실행 토큰 | EC2의 cloudflared가 특정 Tunnel에 연결한다. | AWS Parameter Store |

API 토큰을 Tunnel 실행 토큰으로 사용하지 않는다.

## 4. API 토큰 환경 변수 설정

아래 명령을 실행한다. 입력 요청이 나오면 토큰을 붙여 넣고 Enter를 누른다.
입력값은 화면에 표시하지 않는다.
Bash와 Zsh에서 사용할 수 있다.

```sh
printf 'Cloudflare API token: '
read -r -s CLOUDFLARE_API_TOKEN
printf '\n'
export CLOUDFLARE_API_TOKEN
```

이 설정은 현재 터미널과 여기서 실행한 프로그램에 적용한다.
새 터미널을 열면 다시 설정한다.
토큰 값은 `.tf`, `.tfvars`, 셸 명령 이력이나 Git에 저장하지 않는다.

이 저장소의 `provider "cloudflare" {}`는 환경 변수를 읽는다.
별도의 토큰 변수를 Terraform 파일에 추가할 필요는 없다.
인증 방식은 [Cloudflare 제공자 문서](https://github.com/cloudflare/terraform-provider-cloudflare/blob/v5.28.0/docs/index.md)를 따른다.

## 5. Terraform 변수 입력

최초 설정 시 예제 파일을 복사한다.
이미 변수 파일을 작성했다면 기존 파일을 편집한다.

```sh
cp terraform/cloudflare/terraform.tfvars.example terraform/cloudflare/terraform.tfvars
```

`terraform/cloudflare/terraform.tfvars`를 다음과 같이 편집한다.
아래 식별자와 도메인은 예제다. 실제 값으로 바꾼다.

```hcl
account_id              = "00000000000000000000000000000000"
zone_id                 = "11111111111111111111111111111111"
hostname                = "api.example.com"
tunnel_name             = "openstudy-prod"
origin_service          = "http://127.0.0.1:8080"
enable_api_rate_limit   = false
api_path_prefix         = "/api/"
requests_per_10_seconds = 100
```

| 변수 | 입력 기준 |
| --- | --- |
| `account_id` | 대상 도메인을 소유한 계정 ID를 입력한다. |
| `zone_id` | 대상 기본 도메인의 Zone ID를 입력한다. |
| `hostname` | 외부에 공개할 전체 호스트명을 입력한다. `https://`와 경로는 제외한다. |
| `tunnel_name` | Tunnel의 관리용 이름을 입력한다. |
| `origin_service` | EC2에서 Gateway가 수신할 루프백 HTTP 주소를 입력한다. |
| `enable_api_rate_limit` | 처음에는 `false`로 둔다. 기존 규칙과 API 경로 확인 후 활성화한다. |
| `api_path_prefix` | 요청 제한을 적용할 경로의 시작 부분을 입력한다. |
| `requests_per_10_seconds` | 요청 제한을 활성화할 때 적용할 횟수를 입력한다. |

현재 코드는 `http://127.0.0.1:포트` 형식의 로컬 연결을 지원한다.
`127.0.0.1`은 EC2 자신을 가리키는 주소다.
Gateway의 호스트 포트도 이 값과 일치하게 설정한다.
실제 변수 파일은 `.gitignore`로 Git에서 제외한다.

## 6. 계획 확인과 적용

먼저 제공자를 설치하고 구성 문법을 검사한다.

```sh
terraform -chdir=terraform/cloudflare init
terraform -chdir=terraform/cloudflare validate
terraform -chdir=terraform/cloudflare plan -out=cloudflare.tfplan
```

계획 단계에서 계정 소유권, zone 활성 상태와 호스트명 소속을 확인한다.
처음 구성하는 경우 기본적으로 다음 리소스를 관리한다.

| 리소스 | 설정 |
| --- | --- |
| Tunnel | Cloudflare에서 관리하는 원격 설정 Tunnel |
| Tunnel 연결 설정 | 지정한 호스트명을 로컬 Gateway에 연결하고 나머지는 404로 처리 |
| DNS | `<Tunnel ID>.cfargotunnel.com`을 가리키는 프록시 CNAME |
| SSL/TLS | Full(strict) |
| HTTPS | HTTP 요청을 HTTPS로 이동 |

Full(strict)와 HTTPS 강제 이동은 zone 전체에 적용한다.
같은 zone의 다른 서비스도 이 설정을 지원하는지 확인한다.
Full(strict)는 cloudflared와 로컬 Gateway 사이의 HTTP를 HTTPS로 바꾸지 않는다.
이 구간의 동작은 [Tunnel의 HTTP·HTTPS 연결 안내](https://developers.cloudflare.com/tunnel/troubleshooting/https-origins/)를 참고한다.

동일한 호스트명의 DNS가 이미 있다면 기존 레코드 처리 방법을 먼저 정한다.
state는 Terraform이 관리하는 리소스의 ID와 상태를 기록한 파일이다.
기존 CNAME을 이 구성으로 관리할 경우에는 [DNS import 형식](https://github.com/cloudflare/terraform-provider-cloudflare/blob/v5.28.0/docs/resources/dns_record.md#import)에 따라 state에 가져온다.
이미 다른 state에서 관리하는 리소스는 두 state에 중복 등록하지 않는다.

계획 결과를 확인한 뒤 저장한 계획을 적용한다.

```sh
terraform -chdir=terraform/cloudflare apply cloudflare.tfplan
terraform -chdir=terraform/cloudflare output
```

`terraform/cloudflare`의 state는 이후 변경에도 계속 사용한다.
state를 Git에 올리지 않는다. 보관과 공동 작업 방식은 [구축 절차](setup.md)를 따른다.

## 7. EC2에 Tunnel 연결

Terraform 적용만으로 EC2의 연결이 시작되지는 않는다.
먼저 AWS 구성을 적용해 EC2와 Parameter Store 읽기 권한을 준비한다.
AWS 적용 절차는 [전체 구축 절차](setup.md)를 따른다.

API 토큰 환경 변수가 설정된 터미널에서 다음 명령을 실행한다.
실행자는 대상 AWS 계정의 Parameter Store 쓰기 권한을 사용한다.

```sh
python3 scripts/configure-tunnel.py \
  --account-id "$(terraform -chdir=terraform/cloudflare output -raw account_id)" \
  --tunnel-id "$(terraform -chdir=terraform/cloudflare output -raw tunnel_id)" \
  --parameter-name "$(terraform -chdir=terraform/aws output -raw tunnel_token_parameter_name)" \
  --aws-account-id "$(terraform -chdir=terraform/aws output -raw aws_account_id)" \
  --region "$(terraform -chdir=terraform/aws output -raw aws_region)"
```

이 스크립트는 Tunnel 실행 토큰을 받아 Parameter Store에 SecureString으로 등록한다.
EC2의 cloudflared는 시작할 때 이 값을 읽는다.
최초 토큰 등록 전에는 30초마다 시작을 재시도한다.

Cloudflare의 Tunnel 목록에서 연결 상태가 `Healthy`인지 확인한다.
이미 연결 중인 Tunnel의 토큰을 교체한 경우 EC2에서 서비스를 다시 시작한다.

```sh
sudo systemctl restart cloudflared
```

## 8. 동작 확인

로컬 터미널에서 DNS와 HTTPS를 확인한다.

```sh
task_hostname=$(terraform -chdir=terraform/cloudflare output -raw hostname)
dig +short "$task_hostname"
curl -I "http://$task_hostname"
curl -I "https://$task_hostname"
```

DNS는 Cloudflare 프록시 주소를 응답해야 한다.
HTTP 요청은 같은 호스트의 HTTPS 주소로 이동해야 한다.
HTTPS 접속 시 인증서 오류가 없어야 한다.
Gateway가 아직 없으면 502가 발생할 수 있다.
실제 서비스 동작은 Gateway 배포 후 정상 응답까지 확인한다.

## 선택 설정: WAF와 요청 제한

Free Managed Ruleset은 무료 플랜에서 기본 적용한다.
Terraform은 이 관리형 규칙을 별도로 생성하지 않는다.
대시보드의 적용 상태는 [WAF 시작 안내](https://developers.cloudflare.com/waf/get-started/)를 참고해 확인한다.

요청 제한을 추가하려면 실제 API 경로를 확인한 뒤 다음 값을 변경한다.

```hcl
enable_api_rate_limit   = true
api_path_prefix         = "/api/"
requests_per_10_seconds = 100
```

변경 후 새 `plan`을 만들고 적용한다.
기본 예제는 클라이언트 IP와 Cloudflare 데이터 센터별로 10초 동안 100회를 기준으로 한다.
임계값을 넘으면 10초 동안 차단한다.
무료 플랜은 규칙 하나를 지원한다. 호스트 조건은 지원하지 않는다.
따라서 같은 zone의 모든 호스트에서 `/api/`로 시작하는 경로가 적용 대상이다.
제약은 [플랜별 요청 제한 기능](https://developers.cloudflare.com/waf/rate-limiting-rules/)을 따른다.

기존 `http_ratelimit` 규칙 집합이 있으면 먼저 import하고 기존 규칙을 코드에 보존한다.
현재 코드의 규칙 집합으로 기존 규칙을 덮어쓰지 않도록 계획 결과를 확인한다.

## 자주 발생하는 문제

| 증상 | 확인할 내용 |
| --- | --- |
| 인증 오류 또는 403 | API 토큰의 만료일, Account·Zone 권한과 대상 리소스 범위를 확인한다. |
| 토큰과 API Key 충돌 | 기존 `CLOUDFLARE_API_KEY`, `CLOUDFLARE_EMAIL`, `CLOUDFLARE_API_USER_SERVICE_KEY` 환경 변수 설정을 확인한다. |
| zone 활성 상태 검사 실패 | 네임서버 변경, 도메인 Active 상태와 Cloudflare 일시 중지 여부를 확인한다. |
| 계정 또는 호스트명 검사 실패 | Account ID·Zone ID 조합과 호스트명의 기본 도메인을 확인한다. |
| DNS 레코드 중복 오류 | 같은 호스트명의 기존 DNS와 Terraform state를 확인한다. |
| Tunnel이 Inactive 또는 Down | EC2 가동 상태, Parameter Store 토큰과 cloudflared 서비스 로그를 확인한다. |
| Tunnel은 Healthy지만 502 | `origin_service`와 Gateway의 실행 상태·수신 포트를 확인한다. |
| 무료 플랜의 규칙 제한 오류 | 기존 요청 제한 규칙과 규칙 수를 확인한다. |

작업을 마치면 현재 터미널의 API 토큰을 해제한다.

```sh
unset CLOUDFLARE_API_TOKEN
```
