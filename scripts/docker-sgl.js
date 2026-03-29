#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {process} from 'node:process';

const modelPath = path.resolve('models', 'mistral-7b').replaceAll('\\', '/');

const args = [
	'run',
	'-itd',
	'-p',
	'30000:30000',
	'--shm-size',
	'32g',
	'--gpus',
	'all',
	'-v',
	`${modelPath}:/local/mistral-7b:ro`,
	'--ipc=host',
	'--privileged',
	'--name',
	'sglang',
	'lmsysorg/sglang:dev',
	'python',
	'-m',
	'sglang.launch_server',
	'--model',
	'/local/mistral-7b',
	'--context-length',
	'32000',
	'--tp',
	'1',
	'--quantization',
	'fp8',
	'--kv-cache-dtype',
	'fp8_e5m2',
	'--attention-backend',
	'triton',
	'--chunked-prefill-size',
	'4096',
	'--mem-fraction-static',
	'0.8',
	'--enable-torch-compile',
	'--host',
	'0.0.0.0',
	'--port',
	'30000',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
