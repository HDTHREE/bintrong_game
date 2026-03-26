const { spawnSync } = require('node:child_process');

const cleanup = spawnSync('docker', ['rm', '-f', 'localstack'], { stdio: 'inherit' });

if (cleanup.error) {
  console.error(cleanup.error.message);
  process.exit(1);
}

const args = [
  'run',
  '-d',
  '--rm',
  '--name',
  'localstack',
  '-p',
  '4566:4566',
  '-v',
  '/var/run/docker.sock:/var/run/docker.sock',
  '-e',
  'SERVICES=s3',
  '-e',
  'DEFAULT_REGION=us-east-1',
  '-e',
  'DEBUG=1',
  '-e',
  'LOCALSTACK_ACKNOWLEDGE_ACCOUNT_REQUIREMENT=1',
  'localstack/localstack:latest'
];

const result = spawnSync('docker', args, { stdio: 'inherit' });

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
