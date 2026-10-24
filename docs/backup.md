# Backups and restore

Back up PostgreSQL, not the app container. Keep DB business records and Django session tables together. Treat dumps as private data (sessions included): encrypt, restrict access, avoid Git, and record retention. Production needs automated RDS backups/PITR plus a scheduled restore drill. Restoring a backup can restore old sessions and grants: invalidate sessions and review account state before returning a restored environment to service.

## Local tested round trip

From the repository, with Compose DB running:

```sh
umask 077
mkdir -p /tmp/papradit-backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > /tmp/papradit-backups/papradit.dump
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" papradit_restore_check'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d papradit_restore_check --exit-on-error' < /tmp/papradit-backups/papradit.dump
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d papradit_restore_check -c "SELECT count(*) FROM django_migrations;"'
```

Use a distinct restore DB name each drill or remove **only a verified disposable drill DB**. Never restore over the live database as a test. Compare schema migrations, per-table counts, PR line/request totals, assignments/QC/deliveries and audit rows against the source, then run representative reads under restored credentials. Record time, dump hash and reconciliation outcomes. The development round trip is recorded in `validation.md`; it does not establish RDS PITR or full-history reconciliation.

Production restore: isolate new RDS instance/subnets/security group, restore snapshot/PITR, verify engine/CA and app compatibility, reconcile counts/financial values, revoke all restored sessions, review grants and SMTP/egress, obtain cutover approval, then switch app configuration. Keep original DB read-only and recoverable until approved retention ends. Define business RPO/RTO with owner before launch.
