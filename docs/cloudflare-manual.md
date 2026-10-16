# Cloudflare 수동 설정 범위

## 현재 연결 방식

호스트명은 `openstudy.duckdns.org`을 사용한다.
EC2에서 DuckDNS API를 호출해 공인 IPv4를 자동 반영한다.
설정 방법은 [DuckDNS와 EC2 연동](duckdns.md)을 따른다.

현재 DNS 경로는 다음과 같다.

```text
openstudy.duckdns.org → EC2 공인 IPv4
```

이 경로만으로 Cloudflare 프록시·WAF·Tunnel이 연결되지는 않는다.
Cloudflare는 아직 연결 전이다.
Cloudflare 설정을 추가하는 경우 대시보드에서 수동 수행한다.
현재 배포에서 `terraform/cloudflare`는 사용하지 않는다.

## Tunnel 준비

1. Cloudflare 대시보드의 `Networking` → `Tunnels`에서 Tunnel을 생성한다.
2. cloudflared 연결 방식과 `openstudy-prod` 이름을 사용한다.
3. 생성한 Tunnel의 실행 토큰을 확인한다.
4. AWS Parameter Store에 SecureString으로 등록한다.

토큰 경로는 저장소 루트에서 확인한다.

```sh
terraform -chdir=terraform/aws output -raw tunnel_token_parameter_name
```

기본 경로는 `/openstudy-prod/cloudflared/token`이다.
DuckDNS 토큰의 `/openstudy-prod/duckdns/token`과 구분한다.
파라미터에는 Tunnel 실행 토큰만 입력한다.
EC2 초기 설정이 cloudflared 서비스를 설치하므로 대시보드의 설치 명령을 중복 실행하지 않는다.

Gateway의 로컬 연결 대상은 `http://127.0.0.1:8080`으로 한다.
Tunnel이 Healthy여도 외부 호스트 연결과 HTTPS 인증서가 준비되었는지는 따로 확인한다.
Tunnel 절차는 [공식 시작 안내](https://developers.cloudflare.com/tunnel/get-started/)를 따른다.

## 공개 진입점 결정

Cloudflare에서 공개 요청을 처리하려면 해당 호스트명을 지원하는 연결 방식이 필요하다.
DuckDNS IP 자동 갱신과 Cloudflare의 호스트 등록·인증서 설정은 별도로 검증한다.

Cloudflare for SaaS의 Custom Hostnames를 검토하는 경우 제공자 측 Cloudflare zone이 필요하다.
실제 DNS 레코드와 소유권·인증서 검증 방법이 DuckDNS에서 가능한지도 확인한다.
선행 조건은 [Cloudflare for SaaS 구성 안내](https://developers.cloudflare.com/cloudflare-for-platforms/cloudflare-for-saas/start/getting-started/)를 따른다.
현재는 이 연결 방식을 선택하거나 적용한 상태가 아니다.

Cloudflare 공개 진입점, DNS 경로, HTTPS 인증서와 보호 규칙을 확정한 뒤 문서에 반영한다.
현재 A 레코드의 EC2 직접 연결을 Cloudflare 경유 완료로 기록하지 않는다.

## 서버 검증

EC2에서 실행한다.

```sh
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared --since '-10 min' --no-pager
```

Tunnel을 통한 요청을 확인한 뒤 HTTPS·WAF·요청 제한의 적용 범위를 검증한다.
운영 기록에는 연결 방식과 검증 결과를 남긴다. 토큰 값은 기록하지 않는다.
