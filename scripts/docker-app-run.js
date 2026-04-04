#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import process from 'node:process';

spawnSync('docker', ['rm', '-f', 'livetrivia-app'], {stdio: 'inherit'});

const args = [
	'run',
	'--rm',
	'--name',
	'livetrivia-app',
	'-p',
	'7777:7777',
	'livetrivia-app:latest',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
