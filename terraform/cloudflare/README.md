# 이전 Cloudflare Terraform 예제

현재 운영 기준은 `openstudy.ddns.net`과 Cloudflare 수동 설정이다.
이 디렉터리는 현재 배포에 사용하지 않는다.

이전 코드는 직접 관리하는 Cloudflare zone에 DNS·TLS·Tunnel을 구성하는 예제로 보관한다.
No-IP 호스트명을 이 코드의 `hostname`에 넣어 적용하지 않는다.
현재 구축 절차는 AWS Terraform만 적용한다.

설정 방법은 [Cloudflare 수동 설정](../../docs/cloudflare-manual.md)을 따른다.
`scripts/validate.sh`에 포함된 이 예제의 검사는 모의 테스트로만 수행한다.
