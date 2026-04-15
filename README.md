# service-attendance-registry

## Purpose / Boundary

이 repo는 `기사 x 일자` 근태 truth를 소유하는 Django/DRF runtime repo다.

현재 역할:
- `AttendanceDay` 정본
- `AttendanceSignal` 정본
- dispatch-derived attendance signal sync
- downstream exclusion 판단을 위한 `final_status` 제공

포함하지 않음:
- dispatch plan / upload preview truth
- delivery raw record / daily snapshot truth
- settlement run / settlement item / payout status
- 플랫폼 전체 compose와 gateway 설정

## Runtime Contract / Local Role

- compose service는 `attendance-registry-api` 다.
- gateway prefix는 `/api/attendance/` 다.
- phase 1 current truth는 active source를 `dispatch` 하나만 두는 것이다.
- `00 + zero workload`는 `day_off`, `00 + positive workload`는 `exception`으로 해석한다.

## Local Run / Verification

- local run: `. .venv/bin/activate && python manage.py runserver 0.0.0.0:8000`
- local test: `. .venv/bin/activate && python manage.py test -v 2`

## Image Build / Deploy Contract

- GitHub Actions workflow 이름은 `Build service-attendance-registry image` 다.
- workflow는 immutable `service-attendance-registry:<sha>` 이미지를 ECR로 publish 한다.
- shared ECS deploy, ALB, ACM, Route53 관리는 `../infra-ev-dashboard-platform/` 이 소유한다.

## Environment Files And Safety Notes

- downstream은 prefix root가 아니라 `AttendanceDay`/`AttendanceSignal` read path를 읽는다.
- prod proof는 `/api/attendance/` prefix root가 아니라 실제 protected data path로 잡아야 honest 하다.

## Key Tests Or Verification Commands

- full Django tests: `. .venv/bin/activate && python manage.py test -v 2`
- honest smoke는 `/api/attendance/days/` protected read path까지 포함한다.

## Root Docs / Runbooks

- `../../docs/boundaries/`
- `../../docs/mappings/`
- `../../docs/runbooks/ev-dashboard-ui-smoke-and-decommission.md`
