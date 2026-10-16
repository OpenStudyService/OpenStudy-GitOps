# No-IP 호스트명과 Cloudflare 수동 설정

## 운영 기준

| 항목 | 결정 |
| --- | --- |
| 공개 주소 | `https://openstudy.ddns.net`을 유지한다. |
| DNS 관리 | No-IP에서 관리한다. |
| Cloudflare 설정 | 대시보드에서 수동 수행한다. |
| Terraform 범위 | AWS 네트워크·EC2·IAM과 서버 초기 설정에 적용한다. |
| 현재 상태 | Cloudflare에 아직 연결하지 않았다. |

Cloudflare 설정을 수동으로 변경하는 것과 외부 호스트명의 연결 조건은 별개다.
아래 선행 조건을 확인한 뒤 공개 연결을 진행한다.

## 1. 외부 호스트 연결 조건 확인

No-IP의 Free·Enhanced 호스트명은 네임서버를 변경할 수 없다.
따라서 `openstudy.ddns.net`을 일반 Cloudflare zone으로 이전하는 절차는 사용하지 않는다.
이 제한은 Terraform 사용 여부와 관계없다. [No-IP 공식 제한 사항](https://www.noip.com/support/knowledgebase/free-enhanced-limitations)을 따른다.

Cloudflare에서 외부 호스트명을 처리하는 지원 방식 중 하나는 Cloudflare for SaaS의 Custom Hostnames다.
이는 다른 DNS 사업자에 둔 호스트명을 Cloudflare 서비스에 연결하는 기능이다.
이 방식을 사용하려면 다음 조건을 확인한다.

- Cloudflare에서 이미 관리하는 제공자 측 zone을 준비한다. 이 zone은 `ddns.net`을 뜻하지 않는다.
- 해당 zone에서 Cloudflare for SaaS를 사용할 수 있는지 확인한다.
- No-IP 계정에서 `openstudy.ddns.net` 자체의 CNAME을 설정할 수 있는지 확인한다.
- 호스트명 소유권 검증과 HTTPS 인증서 검증을 모두 완료할 수 있는지 확인한다.

제공자 측 zone을 사용해도 사용자가 접속하는 주소는 `openstudy.ddns.net`으로 유지한다.
현재는 제공자 측 zone과 No-IP의 필요한 DNS 설정 가능 여부를 확인하지 않았다.
이 조건이 충족되기 전에는 공개 연결을 완료로 처리하지 않는다.
Cloudflare for SaaS 활성화 시 요구하는 플랜과 결제 정보도 확인한다.
세부 조건은 [Cloudflare for SaaS 구성](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/start/getting-started/)과 [활성화 안내](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/start/enable/)를 따른다.

## 2. Cloudflare Tunnel 생성

1. [Cloudflare 대시보드](https://dash.cloudflare.com)에 로그인한다.
2. `Networking` → `Tunnels`에서 Tunnel을 생성한다.
3. cloudflared 연결 방식을 선택한다.
4. Tunnel 이름은 `openstudy-prod`로 설정한다.
5. 연결 안내에 표시된 Tunnel ID와 실행 토큰을 확인한다.

AWS 초기 설정은 cloudflared와 systemd 서비스를 설치한다.
대시보드의 설치 명령을 서버에서 중복 실행하지 않는다.
해당 명령에 포함된 실행 토큰 값만 다음 단계에서 사용한다.
Tunnel 생성 절차는 [공식 시작 안내](https://developers.cloudflare.com/tunnel/get-started/)를 따른다.

Tunnel 생성과 `openstudy.ddns.net`의 공개 연결은 별도 단계다.
Tunnel이 만들어졌다는 이유만으로 해당 주소의 DNS·인증서가 구성되었다고 판단하지 않는다.

## 3. 실행 토큰을 AWS에 등록

먼저 [AWS 구축 절차](setup.md)에 따라 EC2를 준비한다.
로컬 저장소 루트에서 토큰을 저장할 경로를 확인한다.

```sh
terraform -chdir=terraform/aws output -raw tunnel_token_parameter_name
```

기본 경로는 `/openstudy-prod/cloudflared/token`이다.
실제 경로는 `name_prefix` 설정에 따라 달라질 수 있으므로 output 값을 사용한다.

1. AWS 콘솔에서 EC2를 생성한 계정과 리전을 선택한다.
2. Systems Manager의 `Parameter Store`로 이동한다.
3. 위 경로의 파라미터를 생성한다.
4. 등급은 `Standard`, 유형은 `SecureString`으로 설정한다.
5. 기본 AWS 관리형 SSM 키를 사용한다.
6. 값에는 Cloudflare Tunnel 실행 토큰만 입력한다.

토큰은 설치 명령 전체나 Terraform 변수 파일에 기록하지 않는다.
서버의 cloudflared는 시작 시 해당 파라미터를 읽는다.
최초 등록 전에는 30초마다 시작을 재시도한다.

기존 토큰을 교체한 경우 EC2에서 다음 명령을 실행한다.

```sh
sudo systemctl restart cloudflared
```

기존 `scripts/configure-tunnel.py`를 사용하는 경우 Account ID와 Tunnel ID를 대시보드에서 확인해 인자로 전달한다.
이 보조 도구는 별도의 Cloudflare API 토큰을 사용한다.
현재 수동 절차에서는 Cloudflare Terraform의 output을 사용하지 않는다.

## 4. 공개 주소와 Gateway 연결

외부 호스트 연결 조건을 충족한 뒤 다음 값을 기준으로 구성한다.

| 항목 | 값 |
| --- | --- |
| 외부 호스트명 | `openstudy.ddns.net` |
| Gateway Service URL | `http://127.0.0.1:8080` |
| DNS 관리 위치 | No-IP |
| 서버 인바운드 | 포트를 열지 않는다. |

Cloudflare for SaaS를 선택하는 경우 다음 순서로 구성한다.

1. 제공자 zone에서 Tunnel로 전달하는 fallback origin을 구성한다.
2. Custom Hostnames에 `openstudy.ddns.net`을 추가한다.
3. No-IP에서 Cloudflare가 안내한 대상 호스트명으로 CNAME을 설정한다.
4. 호스트명 소유권 검증과 인증서 검증을 완료한다.
5. 두 상태가 모두 `active`인지 확인한다.
6. 요청의 Host 값이 `openstudy.ddns.net`일 때도 올바른 Tunnel 경로와 Gateway로 전달되는지 확인한다.

fallback origin은 외부 호스트 요청을 전달할 서버 연결 대상을 뜻한다.
Tunnel을 사용하는 방식은 [Cloudflare의 Tunnel fallback origin 설계](https://developers.cloudflare.com/reference-architecture/design-guides/extending-cloudflares-benefits-to-saas-providers-end-customers/)를 따른다.
실제 제공자 zone과 fallback origin 이름은 설정 시 확정한다.

No-IP의 CNAME 대상을 EC2 공인 IP나 임의의 Tunnel 주소로 추측해 설정하지 않는다.
Cloudflare에서 해당 외부 호스트명과 인증서를 처리하도록 등록한 연결 대상을 사용한다.
No-IP 계정에서 필요한 DNS 또는 검증 레코드를 지원하지 않으면 공개 연결 조건이 충족되지 않는다.

## 5. HTTPS·WAF 확인

수동 설정한 연결 방식에 맞춰 인증서, HTTP → HTTPS 이동과 WAF를 설정한다.
규칙이 실제로 `openstudy.ddns.net`의 요청에 적용되는지 확인한다.
제공자 zone의 설정만으로 외부 호스트의 모든 보호 기능이 완료되었다고 가정하지 않는다.
사용 제품과 플랜의 지원 범위를 확인하고 적용 결과를 기록한다.

Cloudflare에서 EC2까지는 Tunnel을 사용한다.
cloudflared와 Gateway 사이의 `127.0.0.1` 연결은 로컬 HTTP를 사용한다.
TLS 설정은 이 로컬 구간을 HTTPS로 바꾸지 않는다.

## 6. 동작 검증

외부 연결을 구성한 뒤 로컬 터미널에서 실행한다.

```sh
dig +short openstudy.ddns.net CNAME
dig +short openstudy.ddns.net A
curl -I http://openstudy.ddns.net
curl -I https://openstudy.ddns.net
```

2026-10-16 최초 조회에서는 No-IP의 A 레코드를 확인했다.
당시 CNAME 응답은 없었다. 이는 Cloudflare 연결 완료를 증명하지 않는다.

설정 후 DNS가 의도한 Cloudflare 연결 대상으로 향하는지 확인한다.
HTTP는 HTTPS로 이동해야 한다. HTTPS 인증서는 `openstudy.ddns.net`에 유효해야 한다.
Tunnel은 `Healthy` 상태여야 한다.
Gateway 배포 후에는 실제 정상 응답까지 확인한다.

EC2에서는 다음 명령으로 서비스를 확인한다.

```sh
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared --since '-10 min' --no-pager
```

Tunnel이 Healthy여도 공개 주소의 DNS·인증서·애플리케이션 동작은 별도로 검증한다.
계정, 제공자 zone, Tunnel ID, 연결 방식과 검증 결과를 운영 기록에 남긴다.
실행 토큰과 API 토큰은 기록하지 않는다.

## Terraform 실행 범위

현재 배포에서는 `terraform/aws`만 계획하고 적용한다.
`terraform/cloudflare`는 이전 예제로 보관한다.
`scripts/validate.sh`의 Cloudflare 검사는 이전 예제의 모의 테스트다.
수동 설정한 Cloudflare를 Terraform으로 가져오거나 삭제하는 작업은 이 절차에 포함하지 않는다.
