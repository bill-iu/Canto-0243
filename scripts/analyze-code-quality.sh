#!/usr/bin/env bash
# Core code quality analysis — permanently excludes .agents/
fuck-u-code analyze . -l zh-tw --exclude "**/.agents/**"
