#!/usr/bin/env node
/* eslint unicorn/no-process-exit: "off" */
import {spawnSync} from 'node:child_process';
import process from 'node:process';

const args = [
	'build',
	'--file',
	'app.Dockerfile',
	'-t',
	'livetrivia-app:latest',
	'.',
];

const result = spawnSync('docker', args, {stdio: 'inherit'});

if (result.error) {
	console.error(result.error.message);
	process.exit(1);
}

process.exit(result.status ?? 0);
