#!/usr/bin/env python3
"""Private operator-only password-recovery issuer. No public administration API.

Never invoke production issuance through Codex or a recorded/tool terminal.
Requires authenticated local Docker access and an unrecorded controlling TTY.
"""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone


class RecoveryRefused(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise RecoveryRefused(message)


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode()


def fingerprint(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def private_read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as f:
        s = os.fstat(f.fileno())
        require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid() and not s.st_mode & 0o077, 'Protected operator-owned regular file required')
        return json.load(f)


def private_write(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(canonical(value)); f.flush(); os.fsync(f.fileno())


def private_terminal():
    require(all(os.isatty(fd) for fd in (0, 1, 2)), 'Private local terminal required; no pipes or tool terminals')
    tty = os.open('/dev/tty', os.O_RDWR | os.O_NOCTTY)
    require(os.tcgetpgrp(tty) == os.getpgrp() and os.stat(os.ttyname(0)).st_uid == os.getuid(), 'Authenticated foreground operator terminal required')
    return os.fdopen(tty, 'w', buffering=1)


def docker(args, data=None):
    # Ignore Docker contexts/remote endpoints; pin the verified host daemon.
    try:
        r = subprocess.run(['docker', '--host', 'unix:///var/run/docker.sock', *args], input=data,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=True)
        return r.stdout
    except (OSError, subprocess.SubprocessError):
        raise RecoveryRefused('Private operation unconfirmed; do not retry issuance') from None


def verify_host(target):
    require(target['operator_uid'] == os.getuid(), 'Operator UID changed')
    machine = hashlib.sha256(Path('/etc/machine-id').read_bytes().strip()).hexdigest()
    require(machine == target['machine_sha256'], 'Host identity changed')
    require(re.fullmatch('[0-9a-f]{40}', target['revision']), 'Full revision required')
    require(re.fullmatch('[0-9]+', target['cluster']), 'Cluster identity required')
    for key in ('database', 'role'):
        require(re.fullmatch('[a-zA-Z_][a-zA-Z0-9_]*', target[key]), 'Explicit database/role required')
    pg = None
    for prefix in ('api', 'db'):
        require(re.fullmatch('[0-9a-f]{64}', target[f'{prefix}_container']), 'Full container ID required')
        require(re.fullmatch('sha256:[0-9a-f]{64}', target[f'{prefix}_image']), 'Immutable image required')
        c = json.loads(docker(['inspect', target[f'{prefix}_container']]))[0]
        require(c['Id'] == target[f'{prefix}_container'] and c['State']['Running'] and c['Image'] == target[f'{prefix}_image'], 'Container identity/state changed')
        labels = c['Config'].get('Labels') or {}
        require(labels.get('com.docker.compose.project') == 'hypertrophyapp' and labels.get('com.docker.compose.service') == ('api' if prefix == 'api' else 'postgres'), 'Application container ownership differs')
        if prefix == 'api':
            image = json.loads(docker(['image', 'inspect', c['Image']]))[0]
            require(labels.get('org.opencontainers.image.revision') == target['revision'] and image['Config']['Labels'].get('org.opencontainers.image.revision') == target['revision'], 'Application revision changed')
        else:
            require(len(c['Mounts']) == 1 and c['Mounts'][0]['Type'] == 'volume' and c['Mounts'][0]['Name'] == target['volume'] and c['Mounts'][0]['Destination'] == '/var/lib/postgresql/data', 'Production volume changed')
            pg = c
    # Independent socket identity, with no inherited libpq environment or config.
    sql = "SELECT json_build_array(current_database(),current_user,(SELECT system_identifier::text FROM pg_control_system()),(SELECT version_num FROM public.alembic_version))"
    out = docker(['exec', '-i', target['db_container'], 'env', '-i', 'PATH=/usr/local/bin:/usr/bin:/bin', 'psql', '-h', '/var/run/postgresql', '-p', '5432', '-U', target['role'], '-d', target['database'], '-X', '-qAt', '-v', 'ON_ERROR_STOP=1'], ('BEGIN READ ONLY;'+sql+';COMMIT;').encode())
    require(json.loads(out) == [target['database'], target['role'], target['cluster'], target['schema']], 'Independent database identity differs')
    addresses = sorted(n['IPAddress'] for n in pg['NetworkSettings']['Networks'].values() if n['IPAddress'])
    require(addresses == target['server_addresses'], 'Database network identity changed')


def worker(operation, manifest):
    source = Path(__file__).with_name('operator_recovery_worker.py').read_text()
    result = json.loads(docker(['exec', '-i', manifest['target']['api_container'], 'python', '-c', source], canonical({'operation': operation, 'target': manifest['target'], 'state': manifest.get('state')})))
    require('error' not in result, 'Worker outcome unconfirmed; do not retry issuance')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['prepare', 'verify', 'issue'])
    parser.add_argument('--target', help='Protected explicit target JSON for prepare')
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args(argv)
    try:
        with private_terminal() as terminal:
            if args.operation == 'prepare':
                require(args.target, 'Explicit target required')
                target = private_read(args.target)
                verify_host(target)
                manifest = {'format': 1, 'target': target, 'prepared_at': datetime.now(timezone.utc).isoformat()}
                manifest.update(worker('inspect', manifest))
                email = getpass.getpass('Exact login email (hidden, not saved): ').strip().lower()
                require(hashlib.sha256(email.encode()).hexdigest() == manifest['state']['normalized_email_sha256'], 'Account identity does not match')
                del email
                private_write(args.manifest, manifest)
                terminal.write('Prepared only. Manifest SHA256 '+fingerprint(manifest)+'\n')
                return
            manifest = private_read(args.manifest)
            verify_host(manifest['target'])
            require(worker('inspect', manifest)['state'] == manifest['state'], 'Account/recovery inventory changed; renewed approval required')
            digest = fingerprint(manifest)
            if args.operation == 'verify':
                terminal.write('Read-only verification passed. Manifest SHA256 '+digest+'\n')
                return
            approval = getpass.getpass('One-time owner authorization (hidden): ')
            require(approval == 'ISSUE ONE FERRAVIS RECOVERY CODE '+digest, 'Exact separate owner authorization required')
            # Exclusive durable marker prevents a transport/display failure from
            # being retried against this manifest. It never contains a code.
            receipt = args.manifest+'.issuance.json'
            private_write(receipt, {'status': 'attempt_started_outcome_unconfirmed', 'manifest_sha256': digest, 'at': datetime.now(timezone.utc).isoformat()})
            verify_host(manifest['target'])
            result = worker('issue', manifest)
            require(isinstance(result.get('code'), str) and re.fullmatch('[A-Za-z0-9_-]{43}', result['code']), 'Issuance outcome unconfirmed')
            terminal.write('Enter this code once in FERRAVIS within 10 minutes:\n'+result.pop('code')+'\n')
            terminal.flush()
            # Append a secret-free completion receipt only after display.
            private_write(receipt+'.displayed', {'status': 'issued_displayed_once', 'manifest_sha256': digest})
    except Exception:
        # Never echo raw Docker, database, parsing, terminal or credential errors.
        print('Recovery stopped. Outcome may be unconfirmed; inspect the secret-free receipt. No automatic retry.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
