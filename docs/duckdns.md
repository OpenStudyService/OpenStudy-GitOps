# DuckDNS와 EC2 공인 IP 자동 연동

## 동작 방식

`openstudy.duckdns.org`의 A 레코드를 EC2 공인 IPv4로 갱신한다.
Terraform이 갱신 프로그램, EC2 권한과 systemd 실행 주기를 설정한다.
실제 DNS 갱신은 서버에서 수행한다.
EC2 중지·시작으로 IP가 바뀌어도 Terraform을 다시 실행할 필요는 없다.

1. 부팅 후 약 1분부터 갱신 작업을 실행한다. 최대 30초의 임의 지연을 적용한다.
2. EC2 IMDSv2에서 해당 인스턴스의 공인 IPv4를 읽는다.
3. AWS Parameter Store에서 DuckDNS 토큰을 읽는다.
4. DuckDNS HTTPS API로 `openstudy`의 IP를 갱신한다.
5. 이후 15분마다 확인한다. 마지막 성공 IP와 같으면 API 요청을 생략한다.

실행 코드는 `scripts/duckdns-update.py`로 관리한다.
API의 토큰·도메인·IP 입력 형식과 `OK`·`KO` 응답은 [DuckDNS 공식 명세](https://www.duckdns.org/spec.jsp)를 따른다.

## 1. DuckDNS 계정 준비

1. [DuckDNS](https://www.duckdns.org)에 로그인한다.
2. 본인 계정에서 `openstudy`를 등록하거나 기존 등록을 확인한다.
3. 계정의 token 값을 확인한다.

등록한 주소가 `openstudy.duckdns.org`인지 확인한다.
다른 계정이 해당 이름을 소유하고 있다면 본인의 토큰으로 갱신할 수 없다.
토큰은 채팅이나 Git에 기록하지 않는다.

## 2. Terraform 변수 설정

`terraform/aws/terraform.tfvars`에 다음 값을 설정한다.

```hcl
enable_duckdns    = true
duckdns_subdomain = "openstudy"
web_ingress_cidrs = []
```

`duckdns_subdomain`에는 `.duckdns.org`를 제외한 이름만 입력한다.
토큰 값은 Terraform 변수에 넣지 않는다.

저장소 루트에서 AWS 구성을 계획하고 적용한다.

```sh
terraform -chdir=terraform/aws init
terraform -chdir=terraform/aws plan -out=aws.tfplan
terraform -chdir=terraform/aws apply aws.tfplan
terraform -chdir=terraform/aws output
```

신규 EC2는 최초 초기 설정에서 갱신 프로그램을 설치한다.
기존 EC2에 이 초기 설정을 추가하면 서버 교체 계획이 발생할 수 있다.
`prevent_destroy`가 교체를 막으면 보호 설정을 바로 해제하지 않는다.
기존 서버에는 초기 설정의 변경 내용을 검토해 별도로 반영한다.

## 3. 토큰을 Parameter Store에 등록

토큰 저장 경로와 리전을 확인한다.

```sh
terraform -chdir=terraform/aws output -raw duckdns_token_parameter_name
terraform -chdir=terraform/aws output -raw aws_region
```

기본 저장 경로는 `/openstudy-prod/duckdns/token`이다.
실제 경로는 Terraform output 값을 사용한다.

1. AWS 콘솔에서 EC2와 같은 계정·리전을 선택한다.
2. Systems Manager의 Parameter Store로 이동한다.
3. 위 경로에 Standard 등급의 SecureString을 생성한다.
4. 기본 AWS 관리형 SSM 키를 사용한다.
5. 값에는 DuckDNS 계정의 token 문자열만 입력한다.

JSON, API URL이나 셸 명령을 값에 넣지 않는다.
EC2 역할은 이 파라미터 하나만 읽는 권한을 사용한다.
토큰은 Terraform state, user data와 실행 로그에 저장하지 않는다.

최초 등록 후 다음 주기에 갱신 작업을 수행한다.
즉시 갱신하려면 Session Manager로 EC2에 접속해 실행한다.

```sh
sudo systemctl start openstudy-duckdns.service
```

## 4. 동작 확인

EC2 안에서 실행한다.

```sh
sudo systemctl status openstudy-duckdns.timer --no-pager
sudo journalctl -u openstudy-duckdns.service --since '-30 min' --no-pager
```

`DuckDNS update: updated`는 API가 갱신 요청을 승인한 상태다.
`unchanged`는 마지막 성공 IP와 같아서 API 요청을 생략한 상태다.

로컬 터미널에서 두 값을 비교한다.

```sh
terraform -chdir=terraform/aws output -raw public_ipv4
dig +short openstudy.duckdns.org A
```

EC2의 실제 공인 IPv4와 DNS 응답이 같아야 한다.
서버 중지·시작 직후 Terraform output은 이전 IP를 표시할 수 있다.
이 경우 AWS 콘솔의 현재 공인 IPv4로 비교한다.
필요하면 `terraform -chdir=terraform/aws apply -refresh-only`로 state를 갱신한다.
DNS 캐시가 갱신될 시간도 고려한다.

## 5. 웹 포트 설정

IP 연동과 웹 서버 실행은 별도 작업이다.
기본값인 `web_ingress_cidrs = []`는 모든 인바운드 포트를 닫는다.
직접 웹 접속을 허용하려면 다음처럼 설정한 뒤 새 계획을 적용한다.

```hcl
web_ingress_cidrs = ["0.0.0.0/0"]
```

위 예제는 인터넷에서 TCP 80·443 접속을 허용한다.
특정 네트워크만 허용하려면 해당 IPv4 CIDR을 입력한다.
SSH·DB·8080 포트는 이 변수로 열지 않는다.
실제 HTTP·HTTPS 수신 서버와 유효한 인증서는 별도로 구성해야 한다.

Cloudflare Tunnel만으로 접속한다면 빈 목록을 유지한다.
DuckDNS의 A 레코드가 EC2를 직접 가리키는 것만으로 Cloudflare 경유가 설정되지는 않는다.
Cloudflare 작업 범위는 [수동 설정 문서](cloudflare-manual.md)를 따른다.

## 오류 처리

- `KO`나 잘못된 응답을 받으면 반복 갱신을 중단한다.
- 호스트명 소유권과 토큰을 확인한다. 수정 후 Parameter Store 값을 다시 저장해 새 버전을 만든다.
- HTTP 429·5xx와 네트워크 오류는 최소 30분 뒤 다시 시도한다.
- 토큰을 교체한 경우 새 파라미터 버전을 감지해 갱신을 재개한다.
- 토큰을 아직 등록하지 않은 경우 SSM 읽기 오류가 기록된다. 토큰 등록 후 재시도한다.

다른 PC나 공유기의 갱신 프로그램이 같은 주소를 덮어쓰지 않게 한다.
자동 갱신을 끄려면 `enable_duckdns = false`로 설정한다.
기존 서버에서는 타이머도 중지한다.

```sh
sudo systemctl disable --now openstudy-duckdns.timer
```
