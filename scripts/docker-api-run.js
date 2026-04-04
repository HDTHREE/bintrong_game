#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import process from 'node:process';

spawnSync('docker', ['rm', '-f', 'livetrivia-api'], {stdio: 'inherit'});

const args = [
	'run',
	'--rm',
	'--name',
	'livetrivia-api',
	'-p',
	'8000:8000',
	'livetrivia-api:latest',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
