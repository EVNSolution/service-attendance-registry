Source: https://lessons.md

# service-attendance-registry Lessons.md

This service is the independent seed inside the Dispatch Inputs slice. If it does not come up cleanly first, the rest of the slice waits behind it.

The Dockerfile must not ship with `CMD runserver` for production. In ECS that bypasses the default branch in `entrypoint.sh`, so migrations never run and gunicorn never starts.

The safe production container contract is:

- `ENTRYPOINT ["./entrypoint.sh"]`
- no Dockerfile `CMD runserver`
- `entrypoint.sh` runs `python manage.py migrate --noinput`
- `entrypoint.sh` starts gunicorn on `0.0.0.0:8000`

The honest Slice 3 smoke path for this service was `/api/attendance/days/` with admin JWT. The prefix root `/api/attendance/` is only a routing check and can return `404` even when the slice is healthy.
